"""
News Service
─────────────
Interfaces with the Real-Time News Data API on RapidAPI to pull
recent financial and market-related articles.
"""

import requests
from backend.config import settings


# ── Private helpers ───────────────────────────────────────────────

def _rapidapi_headers() -> dict:
    """Build standard RapidAPI request headers for the news endpoint."""
    return {
        "x-rapidapi-key": settings.RAPIDAPI_KEY,
        "x-rapidapi-host": settings.NEWS_API_HOST,
    }


def _extract_articles(data: dict) -> list[dict]:
    """Normalise the API response into a flat list of article dicts."""
    raw = data.get("data", data.get("articles", data.get("news", [])))
    articles = []
    for item in raw:
        articles.append({
            "title":     item.get("title", ""),
            "source":    item.get("source_name", item.get("source", {}).get("name", "")),
            "url":       item.get("link", item.get("url", "")),
            "published": item.get("published_datetime_utc", item.get("published_at", item.get("date", ""))),
            "snippet":   item.get("snippet", item.get("description", item.get("text", ""))),
        })
    return articles


# ── Public API ────────────────────────────────────────────────────

def search_news(query: str, limit: int = 10) -> list[dict]:
    """Search for recent news articles matching *query*.

    Returns a list of normalised article dicts.  On failure the list
    contains a single dict with an ``error`` key.
    """
    url = f"https://{settings.NEWS_API_HOST}/search"
    params = {
        "query":   query,
        "country": "US",
        "lang":    "en",
        "limit":   str(limit),
    }

    try:
        resp = requests.get(url, headers=_rapidapi_headers(), params=params, timeout=15)
        resp.raise_for_status()
        return _extract_articles(resp.json())
    except requests.RequestException as exc:
        return [{"error": str(exc), "query": query}]
