"""
database.py — SQLite engine and session management.

Objectives:
    Provide a singleton SQLAlchemy engine and session factory, lazily
    initialized on first use. Handles database creation (init_db) and
    gives every other module access to DB sessions via get_session().

How it's used:
    Called at CLI startup (cli.py) to initialize the DB schema, and by
    every data-access module (fetcher, scraper, analyzer, discovery) to
    obtain a session for reads/writes. The engine reads DB_PATH from
    config.py dynamically so tests can override it via monkeypatch.

Connections:
    - config.py provides DB_PATH (the SQLite file location).
    - models.py provides the Base class whose metadata is used to create tables.
    - fetcher.py, scraper.py, analyzer.py, discovery.py, cli.py all call
      get_session() to interact with the database.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nonews import config
from nonews.models import Base

_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{config.DB_PATH}", echo=False)
    return _engine


def get_session():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def init_db():
    Base.metadata.create_all(get_engine())
