"""
cli.py — Command-line interface for the nonews system.

Objectives:
    Provide the user-facing CLI with seven commands that cover the full
    news extraction pipeline:
    - fetch: pull articles from RSS sources into the database.
    - scrape: extract full article text for summary-only sources.
    - analyze: run sentiment analysis, opinion generation, and region detection.
    - discover: find new RSS sources automatically.
    - list-sources: show all registered sources and their discovery status.
    - stats: display article counts broken down by source, sentiment, and region.
    - report: generate the HTML dashboard report (D3 template).

How it's used:
    Run via `py -m nonews <command>`. The CLI group initializes the database
    and seeds the source registry on every invocation. Each command lazily
    imports its corresponding module to keep startup fast.

Connections:
    - database.py: init_db() and get_session() called at startup.
    - sources.py: seed_sources() populates the Source table on startup.
    - fetcher.py: fetch_all() called by the `fetch` command.
    - scraper.py: scrape_pending() called by the `scrape` command.
    - analyzer.py: analyze_pending() called by the `analyze` command.
    - discovery.py: discover() called by the `discover` command.
    - generate_report.py: generate() called by the `report` command.
    - models.py: Article, Source, SourceStatus queried by `list-sources` and `stats`.
"""

import logging

import click
from sqlalchemy import func, select

from nonews.database import get_session, init_db
from nonews.models import Article, Source, SourceStatus
from nonews.sources import seed_sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@click.group()
def cli():
    """nonews — Mexican news extraction and analysis system."""
    init_db()
    session = get_session()
    seed_sources(session)
    session.close()


@cli.command()
@click.option("--source", "-s", default=None, help="Fetch a specific source by name")
def fetch(source):
    """Fetch articles from RSS sources."""
    from nonews.fetcher import fetch_all

    total = fetch_all(source_name=source)
    click.echo(f"Done. {total} new articles saved.")


@cli.command()
@click.option("--limit", "-l", default=100, help="Max articles to analyze")
def analyze(limit):
    """Run sentiment analysis on unanalyzed articles."""
    from nonews.analyzer import analyze_pending

    count = analyze_pending(limit=limit)
    click.echo(f"Analyzed {count} articles.")


@cli.command()
@click.option("--limit", "-l", default=50, help="Max articles to scrape")
def scrape(limit):
    """Scrape full article text for summary-only sources."""
    from nonews.scraper import scrape_pending

    count = scrape_pending(limit=limit)
    click.echo(f"Scraped {count} articles.")


@cli.command()
def discover():
    """Discover new RSS sources."""
    from nonews.discovery import discover as run_discovery

    result = run_discovery()
    click.echo(
        f"Discovery complete: {result['new_found']} new sources, "
        f"{result['dormant_retried']} dormant retried."
    )


@cli.command("list-sources")
def list_sources():
    """List all sources and their status."""
    session = get_session()

    click.echo("\n=== Registered Sources ===")
    sources = session.execute(
        select(Source).order_by(Source.name)
    ).scalars().all()
    for s in sources:
        status = "enabled" if s.enabled else "disabled"
        last = s.last_fetched_at.strftime("%Y-%m-%d %H:%M") if s.last_fetched_at else "never"
        error = f" [ERR: {s.last_error}]" if s.last_error else ""
        click.echo(f"  {s.name:30s} {s.category:15s} {status:8s} last: {last}{error}")

    click.echo("\n=== Discovered Source Status ===")
    statuses = session.execute(
        select(SourceStatus).order_by(SourceStatus.status, SourceStatus.domain)
    ).scalars().all()
    if not statuses:
        click.echo("  (none yet — run `nonews discover`)")
    for ds in statuses:
        retry = ds.retry_after.strftime("%Y-%m-%d") if ds.retry_after else "-"
        click.echo(
            f"  {ds.domain:40s} {ds.status:10s} "
            f"fails: {ds.fail_count}  retry: {retry}"
        )

    session.close()


@cli.command()
def stats():
    """Show article statistics."""
    session = get_session()

    total = session.execute(select(func.count(Article.id))).scalar()
    analyzed = session.execute(
        select(func.count(Article.id)).where(Article.analyzed == True)
    ).scalar()

    click.echo(f"\nTotal articles: {total}")
    click.echo(f"Analyzed: {analyzed}")
    click.echo(f"Pending analysis: {total - analyzed}")

    click.echo("\n--- By Source ---")
    by_source = session.execute(
        select(Article.source_name, func.count(Article.id))
        .group_by(Article.source_name)
        .order_by(func.count(Article.id).desc())
    ).all()
    for name, count in by_source:
        click.echo(f"  {name:30s} {count}")

    click.echo("\n--- By Sentiment ---")
    by_sentiment = session.execute(
        select(Article.sentiment, func.count(Article.id))
        .where(Article.sentiment.isnot(None))
        .group_by(Article.sentiment)
    ).all()
    for sentiment, count in by_sentiment:
        click.echo(f"  {sentiment:15s} {count}")

    click.echo("\n--- By Region ---")
    by_region = session.execute(
        select(Article.affected_region, func.count(Article.id))
        .where(Article.affected_region.isnot(None))
        .group_by(Article.affected_region)
        .order_by(func.count(Article.affected_region).desc())
    ).all()
    for region, count in by_region:
        click.echo(f"  {region:20s} {count}")

    session.close()


@cli.command()
@click.option("--output", "-o", default=None, help="Output file path (default: data/report.html)")
def report(output):
    """Generate the HTML dashboard report."""
    from nonews.generate_report import generate

    path = generate("D3", output)
    click.echo(f"Report generated: {path}")


if __name__ == "__main__":
    cli()
