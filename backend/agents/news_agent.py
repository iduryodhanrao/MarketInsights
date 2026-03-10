"""
News / Market-Research Agent  (Agent 4)
───────────────────────────────────────
Searches multiple financial-news queries via RapidAPI Real-Time News,
then uses OpenAI to distil the articles into actionable bullet points
covering the past week's key market developments.
"""

from langchain_openai import ChatOpenAI
from backend.config import settings
from backend.state import MarketState
from backend.services.news_service import search_news

# Diverse queries to capture broad market coverage
SEARCH_QUERIES = [
    "stock market today",
    "technology stocks earnings",
    "commodity prices gold oil",
    "ETF market trends",
    "Federal Reserve interest rates",
]


def fetch_news(state: MarketState) -> dict:
    """Aggregate recent market news and produce a summarised research brief."""

    all_articles: list[dict] = []
    for query in SEARCH_QUERIES:
        all_articles.extend(search_news(query, limit=8))

    # ── LLM-powered research summary ─────────────────────────────
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.1)

    # Truncate to stay within context limits
    articles_for_llm = str(all_articles[:20])

    prompt = (
        "You are a financial research analyst. The articles below were "
        "published in the last week. Produce 5-7 concise bullet points "
        "summarising the most important market-moving developments.\n\n"
        f"Articles:\n{articles_for_llm}\n\n"
        "Focus on actionable insights, earnings surprises, macro events, "
        "and commodity swings."
    )
    summary = llm.invoke(prompt)

    return {
        "news": {
            "articles": all_articles[:15],
            "summary": summary.content,
            "queries_used": SEARCH_QUERIES,
            "total_fetched": len(all_articles),
        }
    }
