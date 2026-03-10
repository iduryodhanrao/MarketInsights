"""
Commodity Agent  (Agent 2)
──────────────────────────
Fetches real-time commodity prices (gold, silver, oil, natural gas,
copper) and generates an AI-driven commodity-market summary.
"""

from langchain_openai import ChatOpenAI
from backend.config import settings
from backend.state import MarketState
from backend.services.yahoo_finance import fetch_quotes, COMMODITY_SYMBOLS


def fetch_commodities(state: MarketState) -> dict:
    """Retrieve commodity quotes and produce a short AI analysis."""

    commodity_quotes = fetch_quotes(COMMODITY_SYMBOLS)

    # ── LLM-powered commodity commentary ─────────────────────────
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
    prompt = (
        "You are a commodities strategist. Summarise the following commodity "
        "price data in 2-3 sentences, noting any significant moves in gold, "
        "oil, or other commodities.\n\n"
        f"Commodities: {commodity_quotes}\n\n"
        "Be factual and succinct."
    )
    analysis = llm.invoke(prompt)

    return {
        "commodities": {
            "quotes": commodity_quotes,
            "analysis": analysis.content,
        }
    }
