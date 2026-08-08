"""
test_discovery.py — Tests for URL/domain utility functions used by source discovery.

Objectives:
    Verify that:
    - Domain extraction from URLs works correctly (strips www., handles paths).
    - Mexican domain detection identifies .mx and .com.mx TLDs.
    - Feed content validation distinguishes real RSS/Atom XML from HTML or plain text.

How it's used:
    Run via `py -m pytest tests/`. Tests pure utility functions that don't
    require network access or database setup. These are the building blocks
    used by the discovery module's more complex strategies.

Connections:
    - tests nonews/discovery.py (_extract_domain, _is_mx_domain, _looks_like_feed).
    - These utilities are used by discover() which is called by the CLI's
      `discover` command to find and validate new RSS sources.
"""

from nonews.discovery import _extract_domain, _is_mx_domain, _looks_like_feed


def test_extract_domain():
    assert _extract_domain("https://www.eluniversal.com.mx/rss") == "eluniversal.com.mx"
    assert _extract_domain("https://expansion.mx/feed") == "expansion.mx"
    assert _extract_domain("http://bbc.com/mundo") == "bbc.com"


def test_is_mx_domain():
    assert _is_mx_domain("eluniversal.com.mx") is True
    assert _is_mx_domain("expansion.mx") is True
    assert _is_mx_domain("bbc.com") is False
    assert _is_mx_domain("reuters.com") is False


def test_looks_like_feed():
    assert _looks_like_feed('<?xml version="1.0"?><rss version="2.0">...') is True
    assert _looks_like_feed('<feed xmlns="http://www.w3.org/2005/Atom">...') is True
    assert _looks_like_feed("<html><body>Not a feed</body></html>") is False
    assert _looks_like_feed("Just plain text") is False
