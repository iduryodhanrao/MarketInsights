"""
Watchlist Agent  (Agent 6)
──────────────────────────
Fetches real-time quotes for the user's watchlist symbols, then
uses the news context and market data to produce BUY / SELL / HOLD
recommendations with grounding source links.
"""

import json
from langchain_openai import ChatOpenAI
from backend.config import settings
from backend.state import MarketState
from backend.services.yahoo_finance import fetch_quotes
from backend.database import get_watchlist, save_recommendations


def evaluate_watchlist(state: MarketState) -> dict:
    """Fetch watchlist quotes, generate AI recommendations, and persist results."""

    watchlist = get_watchlist()
    symbols = [w["symbol"] for w in watchlist]

    if not symbols:
        return {"watchlist": {"quotes": [], "recommendations": [], "count": 0}}

    # ── Fetch live prices for watchlist tickers ──────────────────
    quotes = fetch_quotes(symbols)

    # ── Gather context from other agents for grounded analysis ───
    news_articles = state.get("news", {}).get("articles", [])
    news_summary  = state.get("news", {}).get("summary", "")
    stocks_data   = state.get("stocks", {}).get("analysis", "")
    commodities_data = state.get("commodities", {}).get("analysis", "")

    # ── Build source links from news for grounding ───────────────
    available_sources = []
    for article in news_articles[:15]:
        if article.get("url") and article.get("title"):
            available_sources.append({
                "title": article["title"],
                "url": article["url"],
                "source": article.get("source", ""),
            })

    # ── LLM-powered buy/sell recommendation ──────────────────────
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)

    prompt = (
        "You are a senior investment analyst. Evaluate each stock below and "
        "provide a BUY, SELL, or HOLD recommendation.\n\n"
        f"Watchlist quotes: {quotes}\n\n"
        f"Market context — Stock analysis: {stocks_data}\n"
        f"Commodity analysis: {commodities_data}\n"
        f"News summary: {news_summary}\n\n"
        f"Available news sources for grounding: {json.dumps(available_sources)}\n\n"
        "For EACH symbol, respond in strict JSON array format:\n"
        "[\n"
        '  {{"symbol":"TICKER","signal":"BUY|SELL|HOLD","confidence":"HIGH|MEDIUM|LOW",'
        '"reasoning":"2-3 sentence rationale","sources":[{{"title":"...","url":"..."}}]}}\n'
        "]\n\n"
        "Rules:\n"
        "- Use only the sources provided above for the 'sources' field\n"
        "- Each recommendation MUST include at least 1 source\n"
        "- Reasoning should reference specific price levels or news events\n"
        "- Return ONLY the JSON array, no markdown fences or extra text"
    )

    response = llm.invoke(prompt)
    raw_text = response.content.strip()

    # ── Parse the LLM JSON response ─────────────────────────────
    recs = _parse_recommendations(raw_text, quotes, available_sources)

    # ── Persist recommendations to SQLite ────────────────────────
    save_recommendations(recs)

    return {
        "watchlist": {
            "quotes": quotes,
            "recommendations": recs,
            "count": len(symbols),
        }
    }


def _parse_recommendations(raw: str, quotes: list, fallback_sources: list) -> list[dict]:
    """Parse the LLM JSON output into a clean list of recommendation dicts."""
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        recs = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: generate HOLD for everything if parsing fails
        recs = [{"symbol": q.get("symbol", ""), "signal": "HOLD",
                 "confidence": "LOW", "reasoning": "Unable to parse AI analysis.",
                 "sources": fallback_sources[:1]} for q in quotes]

    # Enrich each rec with price from quotes
    price_map = {q["symbol"]: q.get("price", 0) for q in quotes}
    for rec in recs:
        rec["price"] = price_map.get(rec.get("symbol", ""), 0)
        if not rec.get("sources"):
            rec["sources"] = fallback_sources[:1]

    return recs
