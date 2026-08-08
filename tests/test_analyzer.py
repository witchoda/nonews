"""
test_analyzer.py — Tests for region detection and opinion generation.

Objectives:
    Verify that:
    - Mexican states are correctly detected from article text (e.g., "Jalisco",
      "CDMX", "Nuevo León") using keyword matching.
    - Macro-regions are detected when specific states aren't mentioned
      (e.g., "frontera" → norte, "Bajío" → bajío).
    - Default region is "national" when no location keywords are found.
    - Opinion strings are ≤100 characters and include the sentiment label
      and region.

How it's used:
    Run via `py -m pytest tests/`. Tests the pure-function components of
    the analyzer (region detection and opinion formatting) without requiring
    the pysentimiento model, so they run fast and without heavy dependencies.

Connections:
    - tests nonews/analyzer.py (_detect_region, _generate_opinion).
    - Does NOT test _classify_sentiment (requires pysentimiento model download).
    - These functions are used by analyze_pending() which is called by the
      CLI's `analyze` command.
"""

from nonews.analyzer import _detect_region, _generate_opinion


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
