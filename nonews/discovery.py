"""
discovery.py — Automatic RSS source discovery and lifecycle management.

Objectives:
    Find new Mexican news RSS sources without manual intervention using
    four broad strategies:
    1. Google News Mexico RSS — extract domains from article links.
    2. Article cross-references — extract external .mx domains from stored articles.
    3. Known domain probing — try common RSS URL patterns (/rss, /feed, etc.)
       on a curated list of Mexican news domains.
    4. Homepage scanning — look for <link rel="alternate" type="application/rss+xml">
       tags on discovered homepages.

    Also manages the source lifecycle: new sources are validated and added as
    'active'; failed feeds become 'dormant' with a 14-day retry window; after
    3 consecutive failures they become 'blocked'. Dormant sources are retried
    automatically when their retry_after date passes.

How it's used:
    The CLI's `discover` command runs all strategies in one call. It first
    retries any dormant sources past their retry date, then probes new domains.
    Results are stored in the SourceStatus table (separate from the Source
    table used by the fetcher).

Connections:
    - config.py provides DORMANT_RETRY_DAYS and DORMANT_MAX_RETRIES.
    - models.py defines SourceStatus (created/updated here) and Article
      (read for cross-reference discovery).
    - database.py provides get_session() for DB access.
    - sources.py provides KNOWN_MX_DOMAINS (the curated domain list).
    - cli.py calls discover() from the `discover` command.
    - cli.py list-sources displays SourceStatus entries.
"""

import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from nonews.config import DORMANT_MAX_RETRIES, DORMANT_RETRY_DAYS
from nonews.database import get_session
from nonews.models import Article, SourceStatus

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

RSS_PATH_PATTERNS = [
    "/rss",
    "/feed",
    "/rss.xml",
    "/feed.xml",
    "/atom.xml",
    "/feeds/posts/default",
    "/rss/portada.xml",
    "/rss/ultimas.xml",
]

GOOGLE_NEWS_MX_URL = (
    "https://news.google.com/rss/headlines/section/topic/NATION"
    "?hl=es-419&gl=MX"
)

KNOWN_MX_DOMAINS = [
    "reforma.com", "eluniversal.com.mx", "milenio.com", "proceso.com.mx",
    "animalpolitico.com", "laopinion.com", "elfinanciero.com.mx",
    "expansion.mx", "excelsior.com.mx", "jornada.com.mx",
    "unotv.com", "aztecanoticias.com.mx", "elsiglodetorreon.com.mx",
    "debate.com.mx", "publimetro.com.mx", "infobae.com",
    "heraldodemexico.com.mx", "elsoldemexico.com.mx",
    "elsoldelbajio.com.mx", "elsoldetijuana.com.mx",
    "elsoldeleon.com.mx", "elsoldedurango.com.mx",
    "vanguardia.com.mx", "am.com.mx", "ntv.com.mx",
    "contralinea.com.mx", "laverdadnoticias.com",
    "elimparcial.com", "elnorte.com", "mural.com.mx",
    "mediotiempo.com", "marcar.com", "record.com.mx",
    "estoes.com.mx", "depues.com.mx",
]


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_mx_domain(domain: str) -> bool:
    return domain.endswith(".mx") or domain.endswith(".com.mx")


def _try_feed_url(base_url: str) -> str | None:
    """Try common RSS URL patterns on a domain. Returns the first working URL."""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.hostname}"

    for path in RSS_PATH_PATTERNS:
        feed_url = base + path
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=10, allow_redirects=True)
            if resp.status_code == 200 and _looks_like_feed(resp.text):
                return feed_url
        except requests.RequestException:
            continue
    return None


def _looks_like_feed(text: str) -> bool:
    text_stripped = text.strip()
    if not text_stripped.startswith("<?xml") and not text_stripped.startswith("<"):
        return False
    return "<rss" in text_stripped[:500] or "<feed" in text_stripped[:500]


def _scan_homepage_for_feeds(url: str) -> list[str]:
    """Scan a homepage for RSS/Atom <link> tags."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    feeds = []
    for link in soup.find_all("link", type=re.compile(r"(rss|atom)")):
        href = link.get("href")
        if href:
            if href.startswith("/"):
                parsed = urlparse(url)
                href = f"{parsed.scheme}://{parsed.hostname}{href}"
            feeds.append(href)
    return feeds


def _discover_from_google_news() -> set[str]:
    """Extract domains from Google News Mexico RSS."""
    domains = set()
    try:
        feed = feedparser.parse(GOOGLE_NEWS_MX_URL)
        for entry in feed.entries:
            link = getattr(entry, "link", None)
            if link:
                domain = _extract_domain(link)
                if _is_mx_domain(domain):
                    domains.add(domain)
    except Exception as e:
        logger.warning(f"Google News discovery failed: {e}")
    return domains


def _discover_from_articles(session) -> set[str]:
    """Extract external domains from stored articles."""
    domains = set()
    articles = session.execute(select(Article).limit(500)).scalars().all()
    for article in articles:
        text = article.full_text or article.summary or ""
        urls = re.findall(r'https?://[^\s<>"\']+', text)
        for url in urls:
            domain = _extract_domain(url)
            if _is_mx_domain(domain) and domain not in KNOWN_MX_DOMAINS:
                domains.add(domain)
    return domains


def _discover_from_known_domains() -> set[str]:
    """Try RSS patterns on known Mexican news domains that aren't in our DB yet."""
    domains = set()
    session = get_session()
    existing_domains = {
        _extract_domain(s.feed_url)
        for s in session.execute(select(SourceStatus)).scalars().all()
    }
    session.close()

    for domain in KNOWN_MX_DOMAINS:
        if domain not in existing_domains:
            domains.add(domain)
    return domains


def _validate_feed(feed_url: str) -> bool:
    """Check if a URL is a valid, non-empty RSS feed."""
    try:
        feed = feedparser.parse(feed_url)
        return len(feed.entries) > 0
    except Exception:
        return False


def discover():
    """Run all discovery strategies and update source_status table."""
    session = get_session()
    now = datetime.utcnow()

    new_found = 0
    dormant_retried = 0

    # 1. Retry dormant sources
    dormant = session.execute(
        select(SourceStatus).where(
            SourceStatus.status == "dormant",
            (SourceStatus.retry_after.is_(None)) | (SourceStatus.retry_after <= now),
        )
    ).scalars().all()

    for ds in dormant:
        logger.info(f"Retrying dormant: {ds.domain}")
        dormant_retried += 1
        feed_url = ds.feed_url or _try_feed_url(f"https://{ds.domain}")
        if feed_url and _validate_feed(feed_url):
            ds.status = "active"
            ds.feed_url = feed_url
            ds.last_checked_at = now
            ds.last_error = None
            new_found += 1
            logger.info(f"  Revived: {ds.domain} -> {feed_url}")
        else:
            ds.fail_count += 1
            ds.last_checked_at = now
            if ds.fail_count >= DORMANT_MAX_RETRIES:
                ds.status = "blocked"
                logger.info(f"  Blocked after {ds.fail_count} retries: {ds.domain}")
            else:
                ds.retry_after = now + timedelta(days=DORMANT_RETRY_DAYS)
                logger.info(f"  Still dormant, retry after {DORMANT_RETRY_DAYS}d")

    # 2. Discover new domains from multiple strategies
    new_domains = set()
    new_domains.update(_discover_from_google_news())
    new_domains.update(_discover_from_articles(session))
    new_domains.update(_discover_from_known_domains())

    existing = {
        ds.domain for ds in session.execute(select(SourceStatus)).scalars().all()
    }
    new_domains -= existing

    for domain in new_domains:
        logger.info(f"Probing new domain: {domain}")
        base_url = f"https://{domain}"

        feed_url = _try_feed_url(base_url)
        if not feed_url:
            feeds = _scan_homepage_for_feeds(base_url)
            for f in feeds:
                if _validate_feed(f):
                    feed_url = f
                    break

        if feed_url and _validate_feed(feed_url):
            session.add(SourceStatus(
                domain=domain,
                status="active",
                feed_url=feed_url,
                last_checked_at=now,
            ))
            new_found += 1
            logger.info(f"  New source: {domain} -> {feed_url}")
        else:
            session.add(SourceStatus(
                domain=domain,
                status="dormant",
                last_checked_at=now,
                retry_after=now + timedelta(days=DORMANT_RETRY_DAYS),
            ))
            logger.info(f"  No feed found, marked dormant: {domain}")

    session.commit()
    session.close()

    logger.info(f"Discovery complete: {new_found} new, {dormant_retried} retried")
    return {"new_found": new_found, "dormant_retried": dormant_retried}
