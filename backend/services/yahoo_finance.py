"""
Yahoo Finance Service
─────────────────────
Provides helper functions to fetch real-time market quotes
(stocks, indexes, commodities, ETFs) from the Yahoo Finance
API via RapidAPI.
"""

import requests
from backend.config import settings

# ── Ticker groups referenced by the agents ────────────────────────

STOCK_SYMBOLS     = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
INDEX_SYMBOLS     = ["^GSPC", "^DJI", "^IXIC"]
COMMODITY_SYMBOLS = ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"]
ETF_SYMBOLS       = ["SPY", "QQQ", "VTI", "IWM", "EEM", "GLD", "TLT", "XLF", "ARKK"]

# ── Friendly display names ────────────────────────────────────────

DISPLAY_NAMES = {
    "^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "Nasdaq",
    "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Crude Oil",
    "NG=F": "Natural Gas", "HG=F": "Copper",
}


# ── Private helpers ───────────────────────────────────────────────

def _rapidapi_headers() -> dict:
    """Build standard RapidAPI request headers."""
    return {
        "x-rapidapi-key": settings.RAPIDAPI_KEY,
        "x-rapidapi-host": settings.YAHOO_FINANCE_HOST,
    }


def _safe_number(val) -> float:
    """Extract a numeric value; gracefully handles nested {raw:…} objects."""
    if val is None:
        return 0.0
    raw = val.get("raw", val) if hasattr(val, "get") else val
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def _parse_quotes(data: dict) -> list[dict]:
    """Normalise various Yahoo Finance response shapes into a flat list."""
    # Different API versions wrap results differently
    items = (
        data.get("body")
        or data.get("quoteResponse", {}).get("result")
        or data.get("data")
        or data.get("quotes")
        or []
    )

    quotes = []
    for item in items:
        symbol = item.get("symbol", "")
        quotes.append({
            "symbol":         symbol,
            "name":           item.get("shortName", item.get("longName", DISPLAY_NAMES.get(symbol, symbol))),
            "price":          _safe_number(item.get("regularMarketPrice", item.get("price"))),
            "change":         _safe_number(item.get("regularMarketChange", item.get("change"))),
            "change_percent": _safe_number(item.get("regularMarketChangePercent", item.get("changesPercentage"))),
            "volume":         _safe_number(item.get("regularMarketVolume", item.get("volume"))),
            "market_cap":     _safe_number(item.get("marketCap")),
            "day_high":       _safe_number(item.get("regularMarketDayHigh", item.get("dayHigh"))),
            "day_low":        _safe_number(item.get("regularMarketDayLow", item.get("dayLow"))),
            "prev_close":     _safe_number(item.get("regularMarketPreviousClose", item.get("previousClose"))),
        })
    return quotes


# ── Public API ────────────────────────────────────────────────────

def fetch_quotes(symbols: list[str]) -> list[dict]:
    """Fetch real-time quotes for the given ticker symbols.

    Returns a list of normalised quote dicts, or a single-element list
    containing an error description on failure.
    """
    url = f"https://{settings.YAHOO_FINANCE_HOST}/api/v1/markets/stock/quotes"
    params = {"ticker": ",".join(symbols)}

    try:
        resp = requests.get(url, headers=_rapidapi_headers(), params=params, timeout=15)
        resp.raise_for_status()
        return _parse_quotes(resp.json())
    except requests.RequestException as exc:
        return [{"symbol": s, "name": DISPLAY_NAMES.get(s, s), "price": 0,
                 "change": 0, "change_percent": 0, "error": str(exc)} for s in symbols]
