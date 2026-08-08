"""
models.py — SQLAlchemy ORM models for the nonews database.

Objectives:
    Define the three core tables that store all system state:
    - Article: fetched news articles with metadata, content, and analysis results.
    - Source: registered RSS sources with their configuration and health status.
    - SourceStatus: discovered domains tracked through the discovery lifecycle
      (active → dormant → blocked) with retry scheduling.

How it's used:
    These models are the schema for the SQLite database. Every module that
    reads or writes data interacts with these tables through SQLAlchemy
    sessions. The Article model carries the full pipeline state: from raw
    feed content (summary, full_text) through analysis (sentiment, opinion,
    affected_region).

Connections:
    - database.py uses Base.metadata.create_all() to initialize the schema.
    - fetcher.py creates Article rows from parsed RSS entries.
    - scraper.py updates Article.full_text and content_depth.
    - analyzer.py updates Article.sentiment, opinion, affected_region, analyzed.
    - discovery.py creates and updates SourceStatus rows.
    - cli.py queries all three tables for stats and list-sources commands.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(200), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    author = Column(String(200), nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)
    categories = Column(JSON, nullable=True)
    content_depth = Column(String(20), nullable=False, default="feed")
    opinion = Column(String(100), nullable=True)
    sentiment = Column(String(20), nullable=True)
    affected_region = Column(String(100), nullable=True)
    analyzed = Column(Boolean, nullable=False, default=False)
    is_fake = Column(Boolean, nullable=False, default=False)


class Source(Base):
    __tablename__ = "sources"

    name = Column(String(200), primary_key=True)
    feed_url = Column(String(1000), nullable=False)
    category = Column(String(50), nullable=False, default="national")
    enabled = Column(Boolean, nullable=False, default=True)
    scrape_full_text = Column(Boolean, nullable=False, default=False)
    last_fetched_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)


class SourceStatus(Base):
    __tablename__ = "source_status"

    domain = Column(String(500), primary_key=True)
    status = Column(String(20), nullable=False, default="active")
    feed_url = Column(String(1000), nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    retry_after = Column(DateTime, nullable=True)
    fail_count = Column(Integer, nullable=False, default=0)
