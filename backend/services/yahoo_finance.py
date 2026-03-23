"""
Yahoo Finance Service
─────────────────────
Provides helper functions to fetch real-time market quotes
(stocks, indexes, commodities, ETFs) from the Yahoo Finance
API via RapidAPI.

Also supports market-movers endpoints (top gainers / top losers)
with resilient response parsing across API variants.
"""

import requests
from backend.config import settings

YAHOO_PUBLIC_SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"

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


def _extract_items(data: dict) -> list[dict]:
    """Extract list-like quote collections from varied API response shapes."""
    def _flatten(items: list) -> list[dict]:
        flat: list[dict] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue

            nested = (
                entry.get("quotes")
                or entry.get("items")
                or entry.get("constituents")
                or entry.get("result")
            )

            if isinstance(nested, list):
                flat.extend([x for x in nested if isinstance(x, dict)])
            else:
                flat.append(entry)
        return flat

    candidates = [
        data.get("body"),
        data.get("data"),
        data.get("quotes"),
        data.get("result"),
        data.get("items"),
        data.get("quoteResponse", {}).get("result"),
        data.get("finance", {}).get("result"),
        data.get("gainers"),
        data.get("losers"),
        data.get("top_gainers"),
        data.get("top_losers"),
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            flattened = _flatten(candidate)
            if flattened:
                return flattened
        if isinstance(candidate, dict):
            for value in candidate.values():
                if isinstance(value, list):
                    flattened = _flatten(value)
                    if flattened:
                        return flattened

    return []


def _normalise_quote_item(item: dict) -> dict:
    """Normalise a single quote-like object from any supported endpoint."""
    symbol = item.get("symbol") or item.get("ticker") or item.get("code") or ""
    return {
        "symbol":         symbol,
        "name":           item.get("shortName") or item.get("longName") or item.get("name") or item.get("companyName") or DISPLAY_NAMES.get(symbol, symbol),
        "price":          _safe_number(item.get("regularMarketPrice", item.get("price", item.get("lastPrice")))),
        "change":         _safe_number(item.get("regularMarketChange", item.get("change", item.get("priceChange")))),
        "change_percent": _safe_number(item.get("regularMarketChangePercent", item.get("changePercent", item.get("changesPercentage")))),
        "volume":         _safe_number(item.get("regularMarketVolume", item.get("volume"))),
        "market_cap":     _safe_number(item.get("marketCap")),
        "day_high":       _safe_number(item.get("regularMarketDayHigh", item.get("dayHigh"))),
        "day_low":        _safe_number(item.get("regularMarketDayLow", item.get("dayLow"))),
        "prev_close":     _safe_number(item.get("regularMarketPreviousClose", item.get("previousClose"))),
    }


def _parse_movers(data: dict) -> list[dict]:
    """Parse top-gainer/top-loser endpoint payloads into standard quote objects."""
    parsed = [_normalise_quote_item(item) for item in _extract_items(data)]
    # Keep only valid quote rows with a symbol.
    return [q for q in parsed if q.get("symbol")]


def _fetch_market_movers(paths: list[str], limit: int) -> list[dict]:
    """Try multiple mover endpoints and return the first successful result."""
    params = {"limit": limit, "count": limit, "size": limit}

    for path in paths:
        url = f"https://{settings.YAHOO_FINANCE_HOST}{path}"
        try:
            resp = requests.get(url, headers=_rapidapi_headers(), params=params, timeout=20)
            resp.raise_for_status()
            quotes = _parse_movers(resp.json())
            if quotes:
                return quotes[:limit]
        except requests.RequestException:
            continue

    return []


def _fetch_public_market_movers(scr_id: str, limit: int) -> list[dict]:
    """Fetch market movers from Yahoo's public predefined screener endpoint."""
    params = {
        "formatted": "true",
        "scrIds": scr_id,
        "count": limit,
        "start": 0,
        "lang": "en-US",
        "region": "US",
    }

    try:
        resp = requests.get(
            YAHOO_PUBLIC_SCREENER_URL,
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        resp.raise_for_status()
        return _parse_movers(resp.json())[:limit]
    except requests.RequestException:
        return []


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


def fetch_top_gainers(limit: int = 20) -> list[dict]:
    """Fetch true top market gainers from market-movers endpoints."""
    gainers = _fetch_public_market_movers("day_gainers", limit)
    if gainers:
        return sorted(gainers, key=lambda q: q.get("change_percent", 0), reverse=True)[:limit]

    gainers = _fetch_market_movers(
        paths=[
            "/api/v1/markets/stock/top-gainers",
            "/api/v1/markets/stock/gainers",
            "/api/v1/markets/stock/get-top-gainers",
        ],
        limit=limit,
    )

    # Never fall back to fixed symbols; that would not be true market-wide top gainers.
    return sorted(gainers, key=lambda q: q.get("change_percent", 0), reverse=True)[:limit]


def fetch_top_losers(limit: int = 20) -> list[dict]:
    """Fetch true top market losers from market-movers endpoints."""
    losers = _fetch_public_market_movers("day_losers", limit)
    if losers:
        return sorted(losers, key=lambda q: q.get("change_percent", 0))[:limit]

    losers = _fetch_market_movers(
        paths=[
            "/api/v1/markets/stock/top-losers",
            "/api/v1/markets/stock/losers",
            "/api/v1/markets/stock/get-top-losers",
        ],
        limit=limit,
    )

    # Never fall back to fixed symbols; that would not be true market-wide top losers.
    return sorted(losers, key=lambda q: q.get("change_percent", 0))[:limit]
