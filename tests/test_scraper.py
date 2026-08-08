"""
test_scraper.py — Tests for full-article text extraction from HTML pages.

Objectives:
    Verify that:
    - Article text is correctly extracted from HTML with <article> tags,
      filtering out nav/footer/script noise and short paragraphs.
    - Extraction falls back to all <p> tags when no <article> tag exists.
    - Network failures are handled gracefully (returns None).

How it's used:
    Run via `py -m pytest tests/`. Mocks requests.get to return controlled
    HTML samples, so no real network calls are made during testing.

Connections:
    - tests nonews/scraper.py (extract_article_text).
    - Validates the HTML parsing logic that the scraper module uses to
      enrich articles with full_text when RSS feeds only provide summaries.
"""

from unittest.mock import MagicMock, patch

import pytest


SAMPLE_HTML = """
<html>
<head><title>Test Article</title></head>
<body>
<nav>Navigation menu</nav>
<article>
  <h1>Test Article Title</h1>
  <p>This is a short paragraph that should be filtered out.</p>
  <p>This is a longer paragraph with enough text to be included in the extraction results for testing purposes.</p>
  <p>Another substantial paragraph about Mexican politics and economy that discusses various important topics in detail.</p>
  <p>Final paragraph with more content about the situation in Mexico City and surrounding areas of the country.</p>
</article>
<footer>Footer content</footer>
</body>
</html>
"""


def test_extract_article_text():
    from nonews.scraper import extract_article_text

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_HTML
    mock_resp.raise_for_status = MagicMock()

    with patch("nonews.scraper.requests.get", return_value=mock_resp):
        text = extract_article_text("https://example.com/article")

    assert text is not None
    assert "longer paragraph" in text
    assert "Mexican politics" in text
    assert "Navigation menu" not in text
    assert "Footer content" not in text


def test_extract_article_text_no_article_tag():
    from nonews.scraper import extract_article_text

    html_no_article = """
    <html><body>
    <p>Short.</p>
    <p>This is a substantial paragraph with enough content to pass the minimum length threshold for extraction.</p>
    </body></html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_no_article
    mock_resp.raise_for_status = MagicMock()

    with patch("nonews.scraper.requests.get", return_value=mock_resp):
        text = extract_article_text("https://example.com/page")

    assert text is not None
    assert "substantial paragraph" in text


def test_extract_article_text_request_failure():
    from nonews.scraper import extract_article_text
    import requests

    with patch("nonews.scraper.requests.get", side_effect=requests.RequestException("fail")):
        text = extract_article_text("https://example.com/bad")

    assert text is None
