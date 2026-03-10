"""
Configuration Module
────────────────────
Loads environment variables from .env and provides a centralised
settings object used across the entire backend.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration – all values sourced from environment variables."""

    OPENAI_API_KEY: str   = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str     = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    RAPIDAPI_KEY: str     = os.getenv("RAPIDAPI_KEY", "")

    # RapidAPI host names (override via .env if provider changes)
    YAHOO_FINANCE_HOST: str = os.getenv("YAHOO_FINANCE_HOST", "yahoo-finance15.p.rapidapi.com")
    NEWS_API_HOST: str      = os.getenv("NEWS_API_HOST", "real-time-news-data.p.rapidapi.com")

    # LangSmith tracing (auto-enabled when keys are present)
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "true")
    LANGCHAIN_API_KEY: str    = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str    = os.getenv("LANGCHAIN_PROJECT", "MarketInsights")


settings = Settings()
