"""
scraper.py — Full-article text extraction from web pages.

Objectives:
    For sources whose RSS feeds only provide headlines or short summaries,
    fetch the actual article page and extract the main body text using
    BeautifulSoup. Targets <article> tags when available, falls back to
    all <p> tags, filters out short paragraphs (<40 chars), and strips
    navigation/footer/script noise. Includes rate limiting between requests.

How it's used:
    The CLI's `scrape` command calls scrape_pending(), which queries for
    articles with content_depth='feed' and no full_text yet, fetches each
    article URL, extracts the text, and updates the Article row to
    content_depth='scraped'. Respects SCRAPER_DELAY_SECONDS from config.

Connections:
    - config.py provides SCRAPER_DELAY_SECONDS for rate limiting.
    - models.py defines the Article table (reads and updates full_text, content_depth).
    - database.py provides get_session() for DB access.
    - fetcher.py creates the initial Article rows that this module enriches.
    - analyzer.py benefits from full_text when available (better sentiment accuracy).
    - cli.py calls scrape_pending() from the `scrape` command.
"""

import logging
import time

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from nonews.config import SCRAPER_DELAY_SECONDS
from nonews.database import get_session
from nonews.models import Article

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def extract_article_text(url: str) -> str | None:
    """Fetch a URL and extract the main article text."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Scrape failed for {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    article = soup.find("article")
    if article:
        paragraphs = article.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    text_parts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 40:
            text_parts.append(text)

    if not text_parts:
        return None

    return "\n\n".join(text_parts)


def scrape_pending(limit: int = 50):
    """Scrape full text for articles that have content_depth='feed' and no full_text."""
    session = get_session()
    articles = session.execute(
        select(Article).where(
            Article.full_text.is_(None),
            Article.content_depth == "feed",
        ).limit(limit)
    ).scalars().all()

    scraped = 0
    for article in articles:
        logger.info(f"Scraping: {article.title[:60]}...")
        text = extract_article_text(article.url)
        if text:
            article.full_text = text
            article.content_depth = "scraped"
            scraped += 1
        time.sleep(SCRAPER_DELAY_SECONDS)

    session.commit()
    session.close()
    logger.info(f"Scraped {scraped}/{len(articles)} articles")
    return scraped
