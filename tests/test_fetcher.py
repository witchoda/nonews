"""
test_fetcher.py — Tests for RSS feed parsing, article deduplication, and source registry.

Objectives:
    Verify that:
    - RSS XML is correctly parsed into article dicts (title, URL, categories, etc.).
    - Duplicate articles (same URL) are skipped on repeated saves.
    - The source registry contains all 14 expected sources and lookup works.
    - seed_sources() populates the DB without creating duplicates.

How it's used:
    Run via `py -m pytest tests/`. Uses a temporary SQLite database per test
    (via the temp_db fixture) to ensure isolation. The RSS parsing test
    monkeypatches feedparser.parse to return a fixed XML sample.

Connections:
    - tests nonews/fetcher.py (fetch_source, _save_articles).
    - tests nonews/sources.py (SOURCES list, get_source_by_name, seed_sources).
    - Uses the temp_db and session fixtures defined locally for DB isolation.
"""

import os
import tempfile
from datetime import datetime

import pytest

from nonews import config
from nonews.database import get_engine, get_session, init_db
from nonews.models import Article, Base, Source, SourceStatus


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    db_path = str(tmp_path / "test_nonews.db")
    monkeypatch.setattr(config, "DB_PATH", db_path)

    import nonews.database as db_mod
    db_mod._engine = None
    db_mod._Session = None

    init_db()
    yield db_path

    db_mod._engine = None
    db_mod._Session = None


@pytest.fixture
def session(temp_db):
    sess = get_session()
    yield sess
    sess.close()


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test RSS feed</description>
    <item>
      <title>Article One</title>
      <link>https://example.com/article-1</link>
      <description>Summary of article one about politics in Mexico</description>
      <pubDate>Wed, 06 Aug 2026 10:00:00 GMT</pubDate>
      <category>politics</category>
    </item>
    <item>
      <title>Article Two</title>
      <link>https://example.com/article-2</link>
      <description>Summary of article two about economy</description>
      <pubDate>Thu, 07 Aug 2026 12:00:00 GMT</pubDate>
      <category>economy</category>
    </item>
  </channel>
</rss>"""


def test_fetch_source_parses_rss(monkeypatch):
    import feedparser
    from nonews.fetcher import fetch_source
    from nonews.sources import SourceDef

    original_parse = feedparser.parse
    monkeypatch.setattr(
        feedparser, "parse",
        lambda url: original_parse(SAMPLE_RSS.encode())
    )

    src = SourceDef(
        name="Test", feed_url="https://example.com/rss",
        category="national", content_depth="summary",
    )
    articles = fetch_source(src)

    assert len(articles) == 2
    assert articles[0]["title"] == "Article One"
    assert articles[0]["url"] == "https://example.com/article-1"
    assert articles[0]["source_name"] == "Test"
    assert "politics" in articles[0]["categories"]


def test_save_articles_dedup(session):
    from nonews.fetcher import _save_articles

    articles = [
        {
            "source_name": "Test",
            "title": "Article One",
            "url": "https://example.com/article-1",
            "summary": "Summary one",
            "content_depth": "summary",
        },
        {
            "source_name": "Test",
            "title": "Article Two",
            "url": "https://example.com/article-2",
            "summary": "Summary two",
            "content_depth": "summary",
        },
    ]

    count1 = _save_articles(articles, session)
    assert count1 == 2

    count2 = _save_articles(articles, session)
    assert count2 == 0


def test_source_registry():
    from nonews.sources import SOURCES, get_source_by_name

    assert len(SOURCES) == 14
    assert get_source_by_name("Expansión") is not None
    assert get_source_by_name("nonexistent") is None


def test_seed_sources(session):
    from nonews.sources import seed_sources

    seed_sources(session)
    sources = session.query(Source).all()
    assert len(sources) == 14

    seed_sources(session)
    sources = session.query(Source).all()
    assert len(sources) == 14
