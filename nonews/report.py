"""
report.py — Data extraction for dashboard reports.

Objectives:
    Query the database and produce a JSON structure with all the data
    needed for HTML dashboard visualization: sentiment distribution,
    region breakdown, category breakdown, top articles, timeline,
    and opinion summaries.

Connections:
    - models.py: queries Article table.
    - database.py: provides get_session().
    - generate_report.py: calls build_report_data() and injects into HTML templates.
"""

import json
from collections import Counter
from datetime import datetime

from sqlalchemy import func, select

from nonews.database import get_session, init_db
from nonews.models import Article


def build_report_data(include_fake: bool = True) -> dict:
    """Build a JSON-serializable dict with all dashboard data."""
    init_db()
    session = get_session()

    query = session.query(Article).filter(Article.analyzed == True)
    if not include_fake:
        query = query.filter(Article.is_fake == False)

    articles = query.all()

    # Sentiment distribution (fixed order: positive, negative, neutral)
    sentiments = Counter(a.sentiment for a in articles if a.sentiment)
    sentiment_order = ["positive", "negative", "neutral"]
    sentiment_data = {
        "labels": [s for s in sentiment_order if sentiments.get(s, 0) > 0],
        "values": [sentiments[s] for s in sentiment_order if sentiments.get(s, 0) > 0],
    }

    # Region distribution (top 15)
    regions = Counter(a.affected_region for a in articles if a.affected_region)
    top_regions = regions.most_common(15)
    region_data = {
        "labels": [r[0] for r in top_regions],
        "values": [r[1] for r in top_regions],
    }

    # Category distribution
    categories = Counter()
    for a in articles:
        if a.categories:
            for cat in a.categories:
                categories[cat] += 1
    category_data = {
        "labels": list(categories.keys()),
        "values": list(categories.values()),
    }

    # Top articles by date (most recent 15)
    recent = sorted(articles, key=lambda a: a.published_at or datetime.min, reverse=True)[:15]
    top_articles = []
    for a in recent:
        top_articles.append({
            "title": a.title,
            "sentiment": a.sentiment or "neutral",
            "region": a.affected_region or "national",
            "opinion": a.opinion or "",
            "date": a.published_at.strftime("%Y-%m-%d") if a.published_at else "",
            "is_fake": a.is_fake,
        })

    # Timeline (articles per day, last 30 days)
    timeline = Counter()
    for a in articles:
        if a.published_at:
            day = a.published_at.strftime("%Y-%m-%d")
            timeline[day] += 1
    sorted_days = sorted(timeline.keys())[-30:]
    timeline_data = {
        "labels": sorted_days,
        "values": [timeline[d] for d in sorted_days],
    }

    # Sentiment by region (for stacked chart)
    sentiment_by_region = {}
    for a in articles:
        if a.affected_region and a.sentiment:
            region = a.affected_region
            if region not in sentiment_by_region:
                sentiment_by_region[region] = {"positive": 0, "negative": 0, "neutral": 0}
            sentiment_by_region[region][a.sentiment] += 1

    top_sentiment_regions = sorted(
        sentiment_by_region.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True,
    )[:12]
    sentiment_region_data = {
        "labels": [r[0] for r in top_sentiment_regions],
        "positive": [r[1]["positive"] for r in top_sentiment_regions],
        "negative": [r[1]["negative"] for r in top_sentiment_regions],
        "neutral": [r[1]["neutral"] for r in top_sentiment_regions],
    }

    # Summary stats
    summary = {
        "total": len(articles),
        "positive": sentiments.get("positive", 0),
        "negative": sentiments.get("negative", 0),
        "neutral": sentiments.get("neutral", 0),
        "positive_pct": round(sentiments.get("positive", 0) / max(len(articles), 1) * 100, 1),
        "negative_pct": round(sentiments.get("negative", 0) / max(len(articles), 1) * 100, 1),
        "neutral_pct": round(sentiments.get("neutral", 0) / max(len(articles), 1) * 100, 1),
        "regions_count": len(regions),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Opinion highlights (one per sentiment)
    highlights = {}
    for s in ["positive", "negative", "neutral"]:
        for a in articles:
            if a.sentiment == s and a.opinion and not a.is_fake:
                highlights[s] = {"opinion": a.opinion, "title": a.title}
                break

    session.close()

    return {
        "summary": summary,
        "sentiment": sentiment_data,
        "region": region_data,
        "category": category_data,
        "timeline": timeline_data,
        "sentiment_region": sentiment_region_data,
        "top_articles": top_articles,
        "highlights": highlights,
    }


def build_hierarchy_data(include_fake: bool = True) -> dict:
    """Build hierarchical data: National/International → Region → Category.

    Returns a nested dict suitable for treemap / sunburst visualisations.
    """
    init_db()
    session = get_session()

    query = session.query(Article).filter(Article.analyzed == True)
    if not include_fake:
        query = query.filter(Article.is_fake == False)

    articles = query.all()

    hierarchy: dict = {
        "national": {"total": 0, "regions": {}},
        "international": {"total": 0, "regions": {}},
    }

    for a in articles:
        region = a.affected_region or "national"
        cats = a.categories or ["sin categoria"]

        # International vs National split
        if region == "international":
            branch = "international"
        else:
            branch = "national"

        hierarchy[branch]["total"] += 1

        # Ensure region bucket exists
        if region not in hierarchy[branch]["regions"]:
            hierarchy[branch]["regions"][region] = {"total": 0, "categories": {}}

        hierarchy[branch]["regions"][region]["total"] += 1

        for cat in cats:
            cat_bucket = hierarchy[branch]["regions"][region]["categories"]
            cat_bucket[cat] = cat_bucket.get(cat, 0) + 1

    session.close()
    return hierarchy


def build_sidebar_data(include_fake: bool = True) -> dict:
    """Build article-level data grouped by scope (national/international) and region.
    
    Returns a nested structure with full article details for sidebar navigation
    and filtered views.
    """
    init_db()
    session = get_session()

    query = session.query(Article).filter(Article.analyzed == True)
    if not include_fake:
        query = query.filter(Article.is_fake == False)

    articles = query.all()

    sidebar: dict = {
        "national": {"regions": {}},
        "international": {"regions": {}},
    }

    for a in articles:
        region = a.affected_region or "national"
        
        # Determine scope
        if region == "international":
            scope = "international"
        else:
            scope = "national"

        # Ensure region bucket exists
        if region not in sidebar[scope]["regions"]:
            sidebar[scope]["regions"][region] = []

        # Add article
        sidebar[scope]["regions"][region].append({
            "title": a.title,
            "sentiment": a.sentiment or "neutral",
            "region": region,
            "opinion": a.opinion or "",
            "date": a.published_at.strftime("%Y-%m-%d") if a.published_at else "",
            "summary": a.summary or "",
            "source": a.source_name or "",
            "is_fake": a.is_fake,
        })

    session.close()
    return sidebar


def build_hierarchy_articles_data(include_fake: bool = True) -> dict:
    """Build hierarchical data with full article details for accordion views.

    Returns articles grouped by scope (national/international) -> region,
    each article including title, sentiment, opinion, date, and region.
    Also returns min/max date strings for the date-range slider.
    """
    init_db()
    session = get_session()

    query = session.query(Article).filter(Article.analyzed == True)
    if not include_fake:
        query = query.filter(Article.is_fake == False)

    articles = query.all()

    hierarchy: dict = {
        "national": {"total": 0, "regions": {}},
        "international": {"total": 0, "regions": {}},
    }

    all_dates: list[str] = []

    for a in articles:
        region = a.affected_region or "national"
        date_str = a.published_at.strftime("%Y-%m-%d") if a.published_at else ""

        if region == "international":
            branch = "international"
        else:
            branch = "national"

        hierarchy[branch]["total"] += 1

        if region not in hierarchy[branch]["regions"]:
            hierarchy[branch]["regions"][region] = {"total": 0, "articles": []}

        hierarchy[branch]["regions"][region]["total"] += 1
        hierarchy[branch]["regions"][region]["articles"].append({
            "title": a.title or "",
            "sentiment": a.sentiment or "neutral",
            "opinion": a.opinion or "",
            "date": date_str,
            "region": region,
        })

        if date_str:
            all_dates.append(date_str)

    # Sort articles within each region by date descending
    for branch_key in hierarchy:
        for region_key in hierarchy[branch_key]["regions"]:
            hierarchy[branch_key]["regions"][region_key]["articles"].sort(
                key=lambda x: x["date"], reverse=True
            )

    all_dates.sort()
    date_range = {
        "min": all_dates[0] if all_dates else "",
        "max": all_dates[-1] if all_dates else "",
    }

    session.close()
    return {"hierarchy": hierarchy, "date_range": date_range}
