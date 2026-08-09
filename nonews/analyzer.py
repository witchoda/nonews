"""
analyzer.py — Sentiment analysis, opinion generation, and region detection.

Objectives:
    Process unanalyzed articles through three steps:
    1. Sentiment classification (positive/negative/neutral) using either:
       - "local" backend: pysentimiento, a Spanish-language BERT-based model.
       - "api" backend: Qwen API (DashScope) for richer analysis.
    2. Region detection — identifies which Mexican state or macro-region the
       article is about, using keyword matching against state names and
       regional patterns (norte, bajío, occidente, sureste, centro, golfo, pacífico).
    3. Opinion generation — produces a ≤100 character summary combining the
       sentiment label, affected region, and the article's key sentence.

How it's used:
    The CLI's `analyze` command calls analyze_pending(), which queries for
    articles where analyzed=False, runs all three steps, and writes the
    results back (sentiment, affected_region, opinion, analyzed=True).
    Uses full_text when available, falls back to summary or title.

    Backend selection: set NONEWS_SENTIMENT_BACKEND env var to "local" (default)
    or "api". For API mode, also set NONEWS_SENTIMENT_API_KEY.

Connections:
    - config.py provides SENTIMENT_BACKEND, SENTIMENT_API_KEY, SENTIMENT_API_URL,
      SENTIMENT_API_MODEL settings.
    - models.py defines the Article table (reads text fields, writes analysis fields).
    - database.py provides get_session() for DB access.
    - fetcher.py and scraper.py create the content this module analyzes.
    - cli.py calls analyze_pending() from the `analyze` command.
    - cli.py stats command displays sentiment and region breakdowns.
    - Local mode requires pysentimiento (pip install pysentimiento).
    - API mode requires a DashScope API key (set NONEWS_SENTIMENT_API_KEY).
"""

import logging
import re

import requests
from sqlalchemy import select

from nonews import config
from nonews.database import get_session
from nonews.models import Article

logger = logging.getLogger(__name__)

_sentiment_analyzer = None

MEXICAN_STATES = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
    "Chiapas", "Chihuahua", "Coahuila", "Colima", "Durango",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco",
    "México", "Michoacán", "Morelos", "Nayarit", "Nuevo León",
    "Oaxaca", "Puebla", "Querétaro", "Quintana Roo",
    "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco",
    "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
    "CDMX", "Ciudad de México",
]

STATE_KEYWORDS = {
    "aguascalientes": "Aguascalientes",
    "baja california sur": "Baja California Sur",
    "baja california": "Baja California",
    "campeche": "Campeche",
    "chiapas": "Chiapas",
    "chihuahua": "Chihuahua",
    "coahuila": "Coahuila",
    "colima": "Colima",
    "durango": "Durango",
    "guanajuato": "Guanajuato",
    "guerrero": "Guerrero",
    "hidalgo": "Hidalgo",
    "jalisco": "Jalisco",
    "estado de méxico": "México",
    "edomex": "México",
    "méxico": "México",
    "michoacán": "Michoacán",
    "morelos": "Morelos",
    "nayarit": "Nayarit",
    "nuevo león": "Nuevo León",
    "nuevo leon": "Nuevo León",
    "oaxaca": "Oaxaca",
    "puebla": "Puebla",
    "querétaro": "Querétaro",
    "queretaro": "Querétaro",
    "quintana roo": "Quintana Roo",
    "san luis potosí": "San Luis Potosí",
    "san luis potosi": "San Luis Potosí",
    "sinaloa": "Sinaloa",
    "sonora": "Sonora",
    "tabasco": "Tabasco",
    "tamaulipas": "Tamaulipas",
    "tlaxcala": "Tlaxcala",
    "veracruz": "Veracruz",
    "yucatán": "Yucatán",
    "yucatan": "Yucatán",
    "zacatecas": "Zacatecas",
    "cdmx": "CDMX",
    "ciudad de méxico": "CDMX",
    "ciudad de mexico": "CDMX",
}

REGION_PATTERNS = {
    "norte": ["norte", "frontera", "tijuana", "juárez", "nuevo león", "coahuila", "tamaulipas", "baja california", "sonora", "chihuahua", "durango", "sinaloa"],
    "bajío": ["bajío", "bajio", "guanajuato", "querétaro", "queretaro", "aguascalientes", "san luis potosí", "san luis potosi"],
    "occidente": ["occidente", "jalisco", "colima", "nayarit", "michoacán", "michoacan"],
    "sureste": ["sureste", "chiapas", "tabasco", "oaxaca", "veracruz", "campeche", "yucatán", "yucatan", "quintana roo"],
    "centro": ["centro", "cdmx", "ciudad de méxico", "ciudad de mexico", "estado de méxico", "edomex", "puebla", "morelos", "tlaxcala", "hidalgo"],
    "golfo": ["golfo", "tamaulipas", "veracruz", "tabasco"],
    "pacífico": ["pacífico", "pacifico", "sinaloa", "nayarit", "jalisco", "colima", "michoacán", "michoacan", "oaxaca", "chiapas", "baja california"],
}


def _get_sentiment_analyzer():
    """Lazy-load the local pysentimiento model."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        from pysentimiento import create_analyzer
        _sentiment_analyzer = create_analyzer(task="sentiment", lang="es")
    return _sentiment_analyzer


def _classify_sentiment_local(text: str) -> str:
    """Classify sentiment using the local pysentimiento BERT model."""
    analyzer = _get_sentiment_analyzer()
    result = analyzer.predict(text[:500])
    mapping = {
        "POS": "positive",
        "NEG": "negative",
        "NEU": "neutral",
    }
    return mapping.get(result.output, "neutral")


def _classify_sentiment_api(text: str) -> str:
    """Classify sentiment using an OpenAI-compatible API (Qwen, GPT, etc.)."""
    if not config.SENTIMENT_API_KEY:
        logger.warning("SENTIMENT_API_KEY not set, falling back to local")
        return _classify_sentiment_local(text)

    prompt = (
        "Clasifica el sentimiento de esta noticia mexicana en una sola palabra: "
        "'positive', 'negative', o 'neutral'. Responde solo con la palabra.\n\n"
        f"Noticia: {text[:500]}"
    )

    try:
        resp = requests.post(
            config.SENTIMENT_API_URL,
            headers={
                "Authorization": f"Bearer {config.SENTIMENT_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.SENTIMENT_API_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 10,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"].strip().lower()

        if "positive" in result or "positivo" in result:
            return "positive"
        elif "negative" in result or "negativo" in result:
            return "negative"
        else:
            return "neutral"
    except Exception as e:
        logger.error(f"API sentiment analysis failed: {e}, falling back to local")
        return _classify_sentiment_local(text)


def _classify_sentiment(text: str) -> str:
    """Classify sentiment using the configured backend."""
    if config.SENTIMENT_BACKEND == "api":
        return _classify_sentiment_api(text)
    return _classify_sentiment_local(text)


def _detect_region(text: str) -> str:
    text_lower = text.lower()

    for keyword, state in sorted(STATE_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if keyword in text_lower:
            return state

    for region, keywords in REGION_PATTERNS.items():
        for kw in keywords:
            if kw in text_lower:
                return region

    return "national"


def _generate_opinion(text: str, sentiment: str, region: str) -> str:
    sentences = re.split(r"[.!?]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if sentences:
        key_sentence = sentences[0]
    else:
        key_sentence = text[:80]

    sentiment_label = {
        "positive": "positivo",
        "negative": "negativo",
        "neutral": "neutral",
    }.get(sentiment, "neutral")

    opinion = f"{sentiment_label} para {region}: {key_sentence}"

    if len(opinion) > 100:
        opinion = opinion[:97] + "..."

    return opinion


def analyze_pending(limit: int = 100):
    """Run sentiment analysis on unanalyzed articles."""
    session = get_session()
    articles = session.execute(
        select(Article).where(Article.analyzed == False).limit(limit)
    ).scalars().all()

    analyzed = 0
    for article in articles:
        text = article.full_text or article.summary or article.title
        if not text:
            continue

        try:
            sentiment = _classify_sentiment(text)
            region = _detect_region(text)
            opinion = _generate_opinion(text, sentiment, region)

            article.sentiment = sentiment
            article.affected_region = region
            article.opinion = opinion
            article.analyzed = True
            analyzed += 1
        except Exception as e:
            logger.error(f"Analysis failed for article {article.id}: {e}")

    session.commit()
    session.close()
    logger.info(f"Analyzed {analyzed}/{len(articles)} articles")
    return analyzed
