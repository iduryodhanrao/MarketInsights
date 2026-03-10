"""
ETF Agent  (Agent 3)
────────────────────
Fetches real-time prices for popular ETFs (SPY, QQQ, GLD, etc.)
and generates an AI-driven ETF-market summary.
"""

from langchain_openai import ChatOpenAI
from backend.config import settings
from backend.state import MarketState
from backend.services.yahoo_finance import fetch_quotes, ETF_SYMBOLS


def fetch_etfs(state: MarketState) -> dict:
    """Retrieve ETF quotes and produce a short AI analysis."""

    etf_quotes = fetch_quotes(ETF_SYMBOLS)

    # ── LLM-powered ETF commentary ───────────────────────────────
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
    prompt = (
        "You are an ETF strategist. Summarise the following ETF price data "
        "in 2-3 sentences, highlighting sector rotation or notable fund "
        "flows.\n\n"
        f"ETFs: {etf_quotes}\n\n"
        "Be factual and succinct."
    )
    analysis = llm.invoke(prompt)

    return {
        "etfs": {
            "quotes": etf_quotes,
            "analysis": analysis.content,
        }
    }
