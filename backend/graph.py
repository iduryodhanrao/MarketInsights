"""
LangGraph Workflow
──────────────────
Defines the multi-agent market-insights pipeline.

Topology (fan-out / fan-in / chain):

    START ──┬── fetch_stocks ────────┐
            ├── fetch_commodities ───┤
            ├── fetch_etfs ──────────┼──▶ validate ──▶ evaluate_watchlist ──▶ END
            └── fetch_news ──────────┘

Agents 1-4 execute in parallel; Agent 5 (validate) runs once all
four complete; Agent 6 (watchlist) runs last so it has full context
for buy/sell recommendations.
"""

from langgraph.graph import StateGraph, START, END
from backend.state import MarketState
from backend.agents.stock_agent import fetch_stocks
from backend.agents.commodity_agent import fetch_commodities
from backend.agents.etf_agent import fetch_etfs
from backend.agents.news_agent import fetch_news
from backend.agents.validator_agent import validate_data
from backend.agents.watchlist_agent import evaluate_watchlist


def build_graph() -> StateGraph:
    """Construct and compile the LangGraph workflow."""

    builder = StateGraph(MarketState)

    # ── Register agent nodes ─────────────────────────────────────
    builder.add_node("fetch_stocks", fetch_stocks)
    builder.add_node("fetch_commodities", fetch_commodities)
    builder.add_node("fetch_etfs", fetch_etfs)
    builder.add_node("fetch_news", fetch_news)
    builder.add_node("validate", validate_data)
    builder.add_node("evaluate_watchlist", evaluate_watchlist)

    # ── Fan-out: all fetch agents launch from START in parallel ──
    builder.add_edge(START, "fetch_stocks")
    builder.add_edge(START, "fetch_commodities")
    builder.add_edge(START, "fetch_etfs")
    builder.add_edge(START, "fetch_news")

    # ── Fan-in: validator waits for every fetcher to finish ──────
    builder.add_edge("fetch_stocks", "validate")
    builder.add_edge("fetch_commodities", "validate")
    builder.add_edge("fetch_etfs", "validate")
    builder.add_edge("fetch_news", "validate")

    # ── Chain: watchlist agent runs after validator ───────────────
    builder.add_edge("validate", "evaluate_watchlist")

    # ── Terminal edge ────────────────────────────────────────────
    builder.add_edge("evaluate_watchlist", END)

    return builder.compile()


# Pre-compiled graph instance used by the API layer
market_graph = build_graph()
