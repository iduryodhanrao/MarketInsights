"""
Stock Agent  (Agent 1)
─────────────────────
Fetches true top-20 market gainers and top-20 market losers,
then uses OpenAI to produce a brief analytical summary.
"""

from langchain_openai import ChatOpenAI
from backend.config import settings
from backend.state import MarketState
from backend.services.yahoo_finance import fetch_top_gainers, fetch_top_losers


def fetch_stocks(state: MarketState) -> dict:
    """Retrieve top gainers/losers and generate a short AI analysis."""

    stock_quotes = fetch_top_gainers(limit=20)
    index_quotes = fetch_top_losers(limit=20)

    # ── LLM-powered market commentary ────────────────────────────
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
    prompt = (
        "You are a senior equity analyst. Given the data below, write a concise "
        "2-3 sentence market commentary highlighting notable top gainers, top losers, "
        "and what this implies for market sentiment.\n\n"
        f"Top 20 Gainers: {stock_quotes}\n"
        f"Top 20 Losers: {index_quotes}\n\n"
        "Be factual and succinct."
    )
    analysis = llm.invoke(prompt)

    return {
        "stocks": {
            "stock_quotes": stock_quotes,
            "index_quotes": index_quotes,
            "analysis": analysis.content,
        }
    }
