"""
test_analyzer.py — Tests for region detection, opinion generation, and sentiment backends.

Objectives:
    Verify that:
    - Mexican states are correctly detected from article text (e.g., "Jalisco",
      "CDMX", "Nuevo León") using keyword matching.
    - Macro-regions are detected when specific states aren't mentioned
      (e.g., "frontera" → norte, "Bajío" → bajío).
    - Default region is "national" when no location keywords are found.
    - Opinion strings are ≤100 characters and include the sentiment label
      and region.
    - API sentiment backend correctly parses responses and falls back to local
      on errors.

How it's used:
    Run via `py -m pytest tests/`. Tests the pure-function components of
    the analyzer (region detection, opinion formatting, API parsing) without
    requiring the pysentimiento model or real API calls.

Connections:
    - tests nonews/analyzer.py (_detect_region, _generate_opinion, _classify_sentiment_api).
    - Does NOT test _classify_sentiment_local (requires pysentimiento model download).
    - These functions are used by analyze_pending() which is called by the
      CLI's `analyze` command.
"""

from unittest.mock import MagicMock, patch

from nonews.analyzer import _classify_sentiment_api, _detect_region, _generate_opinion


def test_detect_region_specific_state():
    assert _detect_region("El gobernador de Jalisco anunció nuevas medidas") == "Jalisco"
    assert _detect_region("Situación en CDMX por las lluvias") == "CDMX"
    assert _detect_region("Nuevo León reporta incremento económico") == "Nuevo León"


def test_detect_region_macro_region():
    assert _detect_region("La frontera norte enfrenta retos migratorios") == "norte"
    assert _detect_region("El Bajío industrial crece este trimestre") == "bajío"


def test_detect_region_default_national():
    assert _detect_region("El presidente anunció nuevas políticas federales") == "national"


def test_generate_opinion_length():
    opinion = _generate_opinion(
        "El gobierno anunció nuevas medidas económicas que beneficiarán a millones.",
        "positive",
        "national",
    )
    assert len(opinion) <= 100
    assert "positivo" in opinion
    assert "national" in opinion


def test_generate_opinion_negative():
    opinion = _generate_opinion(
        "La violencia en Zacatecas sigue incrementándose sin control.",
        "negative",
        "Zacatecas",
    )
    assert "negativo" in opinion
    assert "Zacatecas" in opinion


def test_api_sentiment_positive():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "positive"}}]
    }

    with patch("nonews.analyzer.config") as mock_config:
        mock_config.SENTIMENT_API_KEY = "test-key"
        mock_config.SENTIMENT_API_URL = "https://api.test.com"
        mock_config.SENTIMENT_API_MODEL = "test-model"
        with patch("nonews.analyzer.requests.post", return_value=mock_resp):
            result = _classify_sentiment_api("Noticia muy buena para México")

    assert result == "positive"


def test_api_sentiment_negative():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "negativo"}}]
    }

    with patch("nonews.analyzer.config") as mock_config:
        mock_config.SENTIMENT_API_KEY = "test-key"
        mock_config.SENTIMENT_API_URL = "https://api.test.com"
        mock_config.SENTIMENT_API_MODEL = "test-model"
        with patch("nonews.analyzer.requests.post", return_value=mock_resp):
            result = _classify_sentiment_api("Crisis económica en el país")

    assert result == "negative"


def test_api_sentiment_no_key_falls_back():
    """When API key is not set, should fall back to local backend."""
    with patch("nonews.analyzer.config") as mock_config:
        mock_config.SENTIMENT_API_KEY = ""
        with patch("nonews.analyzer._classify_sentiment_local", return_value="neutral"):
            result = _classify_sentiment_api("Some text")

    assert result == "neutral"


def test_api_sentiment_error_falls_back():
    """When API call fails, should fall back to local backend."""
    import requests as req

    with patch("nonews.analyzer.config") as mock_config:
        mock_config.SENTIMENT_API_KEY = "test-key"
        mock_config.SENTIMENT_API_URL = "https://api.test.com"
        mock_config.SENTIMENT_API_MODEL = "test-model"
        with patch("nonews.analyzer.requests.post", side_effect=req.RequestException("fail")):
            with patch("nonews.analyzer._classify_sentiment_local", return_value="neutral"):
                result = _classify_sentiment_api("Some text")

    assert result == "neutral"
