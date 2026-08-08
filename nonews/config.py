"""
config.py — Central configuration for the nonews system.

Objectives:
    Define all shared constants, paths, and tunable parameters used across
    the application: database location, article categories, scraper delays,
    and source-discovery lifecycle settings.

How it's used:
    Imported by nearly every other module. The DB_PATH can be overridden
    via the NONEWS_DB_PATH environment variable. CATEGORIES defines the
    fixed set of news categories the system recognizes.

Connections:
    - database.py reads DB_PATH to locate the SQLite file.
    - sources.py uses CATEGORIES for validation context.
    - scraper.py reads SCRAPER_DELAY_SECONDS for rate limiting.
    - discovery.py reads DORMANT_RETRY_DAYS and DORMANT_MAX_RETRIES
      to manage the source lifecycle (active → dormant → blocked).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = os.environ.get("NONEWS_DB_PATH", str(DATA_DIR / "nonews.db"))

CATEGORIES = [
    "politics",
    "economy",
    "security",
    "energy",
    "education",
    "health",
    "infrastructure",
    "international",
    "regional",
    "justice",
    "environment",
    "technology",
    "culture",
    "opinion",
]

SCRAPER_DELAY_SECONDS = 2.0
DORMANT_RETRY_DAYS = 14
DORMANT_MAX_RETRIES = 3
