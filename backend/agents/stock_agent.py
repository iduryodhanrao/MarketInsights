"""
Stock Agent  (Agent 1)
─────────────────────
Fetches real-time prices for major tech stocks and market indexes,
then uses OpenAI to produce a brief analytical summary.
"""

from langchain_openai import ChatOpenAI
from backend.config import settings
from backend.state import MarketState
from backend.services.yahoo_finance import fetch_quotes, STOCK_SYMBOLS, INDEX_SYMBOLS


def fetch_stocks(state: MarketState) -> dict:
    """Retrieve stock and index quotes, then generate a short AI analysis."""

    stock_quotes = fetch_quotes(STOCK_SYMBOLS)
    index_quotes = fetch_quotes(INDEX_SYMBOLS)

    # ── LLM-powered market commentary ────────────────────────────
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
    prompt = (
        "You are a senior equity analyst. Given the data below, write a concise "
        "2-3 sentence market commentary highlighting notable movers and overall "
        "market direction.\n\n"
        f"Stocks: {stock_quotes}\n"
        f"Indexes: {index_quotes}\n\n"
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
