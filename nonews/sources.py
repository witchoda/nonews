"""
sources.py — Registry of verified RSS news sources.

Objectives:
    Define the 14 known Mexican and international news sources that provide
    free RSS/Atom feeds. Each source is described as a SourceDef with its
    feed URL, category (national/regional/international), content depth
    (full/summary/headline), and whether full-text scraping is needed.
    Also provides seed_sources() to populate the Source table in the DB.

How it's used:
    The SOURCES list is the master input for the fetcher — it iterates over
    these definitions to know which URLs to fetch and how to classify the
    results. The CLI's --source flag matches against source names here.
    seed_sources() is called at CLI startup to ensure the DB has a row for
    each source.

Connections:
    - fetcher.py imports SOURCES and SourceDef to iterate and fetch feeds.
    - models.py defines the Source table that seed_sources() populates.
    - database.py provides the session used by seed_sources().
    - cli.py calls seed_sources() during initialization.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDef:
    name: str
    feed_url: str
    category: str  # national, regional, international
    content_depth: str  # full, summary, headline
    scrape_full_text: bool = False


SOURCES: list[SourceDef] = [
    SourceDef(
        name="Expansión",
        feed_url="https://expansion.mx/rss",
        category="national",
        content_depth="full",
    ),
    SourceDef(
        name="El Financiero",
        feed_url="https://www.elfinanciero.com.mx/rss",
        category="national",
        content_depth="full",
    ),
    SourceDef(
        name="El Sol de México",
        feed_url="https://www.elsoldemexico.com.mx/rss",
        category="national",
        content_depth="summary",
        scrape_full_text=True,
    ),
    SourceDef(
        name="Vanguardia",
        feed_url="https://www.vanguardia.com.mx/rss",
        category="regional",
        content_depth="full",
    ),
    SourceDef(
        name="BBC Mundo",
        feed_url="https://feeds.bbci.co.uk/mundo/rss.xml",
        category="international",
        content_depth="headline",
    ),
    SourceDef(
        name="Excélsior",
        feed_url="https://www.excelsior.com.mx/rss",
        category="national",
        content_depth="full",
    ),
    SourceDef(
        name="Contralínea",
        feed_url="https://www.contralinea.com.mx/feed",
        category="national",
        content_depth="summary",
    ),
    SourceDef(
        name="Periódico AM",
        feed_url="https://www.am.com.mx/feed",
        category="regional",
        content_depth="full",
    ),
    SourceDef(
        name="La Verdad Noticias",
        feed_url="https://laverdadnoticias.com/feed",
        category="national",
        content_depth="summary",
    ),
    SourceDef(
        name="NTV+",
        feed_url="https://www.ntv.com.mx/rss",
        category="regional",
        content_depth="summary",
    ),
    SourceDef(
        name="El Sol de León",
        feed_url="https://www.elsoldeleon.com.mx/rss",
        category="regional",
        content_depth="summary",
        scrape_full_text=True,
    ),
    SourceDef(
        name="El Sol de Tijuana",
        feed_url="https://www.elsoldetijuana.com.mx/rss",
        category="regional",
        content_depth="summary",
        scrape_full_text=True,
    ),
    SourceDef(
        name="El Sol del Bajío",
        feed_url="https://www.elsoldelbajio.com.mx/rss",
        category="regional",
        content_depth="summary",
        scrape_full_text=True,
    ),
    SourceDef(
        name="El Sol de Durango",
        feed_url="https://www.elsoldedurango.com.mx/rss",
        category="regional",
        content_depth="summary",
        scrape_full_text=True,
    ),
]


def get_source_by_name(name: str) -> SourceDef | None:
    for src in SOURCES:
        if src.name.lower() == name.lower():
            return src
    return None


def seed_sources(session):
    """Insert source definitions into the DB if they don't exist yet."""
    from nonews.models import Source

    for src in SOURCES:
        existing = session.get(Source, src.name)
        if existing is None:
            session.add(
                Source(
                    name=src.name,
                    feed_url=src.feed_url,
                    category=src.category,
                    enabled=True,
                    scrape_full_text=src.scrape_full_text,
                )
            )
    session.commit()
