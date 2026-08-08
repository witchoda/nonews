"""
fetcher.py — RSS feed fetching and article ingestion.

Objectives:
    Parse RSS/Atom feeds using feedparser, extract article metadata
    (title, URL, date, author, summary, categories), normalize dates
    to datetime objects, strip HTML entities, and save new articles to
    the database with URL-based deduplication (skip if URL already exists).

How it's used:
    The CLI's `fetch` command calls fetch_all(), which iterates over all
    enabled sources (or a single named source), fetches each feed, and
    saves new articles. Each source's last_fetched_at and last_error are
    updated in the Source table after each attempt.

Connections:
    - sources.py provides the SOURCES list and SourceDef type.
    - models.py defines Article (written here) and Source (status updated here).
    - database.py provides get_session() for DB access.
    - cli.py calls fetch_all() from the `fetch` command.
    - scraper.py later enriches articles that have content_depth='feed'.
    - analyzer.py later analyzes articles that have analyzed=False.
"""

import html
import logging
from datetime import datetime
from time import mktime

import feedparser
from sqlalchemy import select

from nonews.database import get_session
from nonews.models import Article, Source
from nonews.sources import SOURCES, SourceDef

logger = logging.getLogger(__name__)


def _parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed))
            except Exception:
                pass
    return None


def _extract_content(entry) -> str | None:
    if hasattr(entry, "content") and entry.content:
        return entry.content[0].get("value", "")
    if hasattr(entry, "summary"):
        return entry.summary
    return None


def _strip_html(text: str | None) -> str | None:
    if text is None:
        return None
    return html.unescape(text).strip()


def fetch_source(source_def: SourceDef) -> list[dict]:
    """Fetch a single RSS source and return new articles as dicts."""
    logger.info(f"Fetching {source_def.name}: {source_def.feed_url}")
    feed = feedparser.parse(source_def.feed_url)

    if feed.bozo and not feed.entries:
        logger.warning(f"Feed error for {source_def.name}: {feed.bozo_exception}")
        return []

    articles = []
    for entry in feed.entries:
        link = getattr(entry, "link", None)
        if not link:
            continue

        articles.append(
            {
                "source_name": source_def.name,
                "title": getattr(entry, "title", ""),
                "url": link,
                "author": getattr(entry, "author", None),
                "published_at": _parse_date(entry),
                "summary": _strip_html(_extract_content(entry)),
                "categories": [
                    t.get("term", "")
                    for t in getattr(entry, "tags", [])
                    if t.get("term")
                ],
                "content_depth": source_def.content_depth,
            }
        )

    logger.info(f"  Found {len(articles)} items from {source_def.name}")
    return articles


def _save_articles(articles: list[dict], session):
    """Save articles to DB, skipping duplicates by URL."""
    new_count = 0
    for art in articles:
        exists = session.execute(
            select(Article).where(Article.url == art["url"])
        ).scalar_one_or_none()
        if exists:
            continue
        session.add(Article(**art))
        new_count += 1
    session.commit()
    return new_count


def _update_source_status(source_name: str, error: str | None, session):
    now = datetime.utcnow()
    source = session.get(Source, source_name)
    if source:
        source.last_fetched_at = now
        source.last_error = error
        session.commit()


def fetch_all(source_name: str | None = None):
    """Fetch all enabled sources (or a specific one). Returns total new articles."""
    session = get_session()
    targets = SOURCES
    if source_name:
        targets = [s for s in SOURCES if s.name.lower() == source_name.lower()]
        if not targets:
            logger.error(f"Unknown source: {source_name}")
            return 0

    total_new = 0
    for src_def in targets:
        db_source = session.get(Source, src_def.name)
        if db_source and not db_source.enabled:
            logger.info(f"Skipping disabled source: {src_def.name}")
            continue

        try:
            articles = fetch_source(src_def)
            new_count = _save_articles(articles, session)
            _update_source_status(src_def.name, None, session)
            total_new += new_count
            logger.info(f"  Saved {new_count} new articles")
        except Exception as e:
            logger.error(f"Error fetching {src_def.name}: {e}")
            _update_source_status(src_def.name, str(e), session)

    session.close()
    return total_new
