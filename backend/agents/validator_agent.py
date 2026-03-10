"""
Validator Agent  (Agent 5)
──────────────────────────
Evaluates the data collected by Agents 1-4 for freshness and
relevance.  Checks the system clock against reported timestamps
and uses OpenAI to produce a confidence-scored validation report.
"""

from datetime import datetime
from langchain_openai import ChatOpenAI
from backend.config import settings
from backend.state import MarketState


def validate_data(state: MarketState) -> dict:
    """Validate that all collected market data is recent, complete, and relevant."""

    current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Build a compact snapshot for the LLM ─────────────────────
    snapshot = {
        "system_time":       current_dt,
        "pipeline_start":    state.get("timestamp", ""),
        "stocks_present":    bool(state.get("stocks", {}).get("stock_quotes")),
        "indexes_present":   bool(state.get("stocks", {}).get("index_quotes")),
        "commodities_present": bool(state.get("commodities", {}).get("quotes")),
        "etfs_present":      bool(state.get("etfs", {}).get("quotes")),
        "news_articles":     state.get("news", {}).get("total_fetched", 0),
    }

    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
    prompt = (
        "You are a data-quality analyst. The current system date/time is "
        f"{current_dt}. The pipeline was invoked at "
        f"{state.get('timestamp', 'unknown')}.\n\n"
        "Below is a presence/count summary of each data section, followed by "
        "the raw data itself.\n\n"
        f"Availability snapshot: {snapshot}\n\n"
        f"Stocks data:      {state.get('stocks', {})}\n"
        f"Commodities data: {state.get('commodities', {})}\n"
        f"ETFs data:        {state.get('etfs', {})}\n"
        f"News data:        {state.get('news', {})}\n\n"
        "Produce a short validation report (3-5 sentences) covering:\n"
        "1. Whether data is recent (within the last trading session).\n"
        "2. Completeness — any missing sections or symbols.\n"
        "3. Overall confidence: HIGH / MEDIUM / LOW.\n"
        "End with a single line: STATUS: <HIGH|MEDIUM|LOW>"
    )
    report = llm.invoke(prompt)

    # ── Extract status keyword from the last line ────────────────
    report_text = report.content
    status = "MEDIUM"
    for line in reversed(report_text.splitlines()):
        if "STATUS:" in line.upper():
            status = line.split(":")[-1].strip().upper()
            break

    return {
        "validation": {
            "status":      status,
            "system_time": current_dt,
            "report":      report_text,
        }
    }
