"""
Graph State Definition
──────────────────────
Defines the shared state schema that flows through every node
in the LangGraph market-insights pipeline.
"""

from typing import TypedDict


class MarketState(TypedDict):
    """Shared state passed between all agents in the workflow.

    Each agent writes to its own key; the validator reads all keys.
    - stocks      : populated by Agent 1 (stock_agent)
    - commodities : populated by Agent 2 (commodity_agent)
    - etfs        : populated by Agent 3 (etf_agent)
    - news        : populated by Agent 4 (news_agent)
    - validation  : populated by Agent 5 (validator_agent)
    - watchlist   : populated by Agent 6 (watchlist_agent)
    - timestamp   : ISO-8601 timestamp set at invocation time
    """
    stocks: dict
    commodities: dict
    etfs: dict
    news: dict
    validation: dict
    watchlist: dict
    timestamp: str
