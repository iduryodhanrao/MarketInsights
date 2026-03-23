---
title: Market Insights
emoji: 📈
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Market Insights — AI-Powered Financial Dashboard

A multi-agent market insights platform built with **LangGraph**, **OpenAI**, and **RapidAPI**.  
Five specialised AI agents run in parallel to fetch, analyse, and validate real-time market data.

---

## Architecture

```
START ──┬── Agent 1 (Stocks-gainers/losers)┐
        ├── Agent 2 (Commodities) ─────────┤
        ├── Agent 3 (ETFs) ────────────────┼──▶ Agent 5 (Validator) ──▶ END
        └── Agent 4 (News & Research) ─────┘
```

| Component | Technology |
|-----------|-----------|
| **Agent Framework** | LangGraph (fan-out / fan-in) |
| **LLM** | OpenAI GPT-4o-mini |
| **Tracing** | LangSmith |
| **Market Data** | RapidAPI — Yahoo Finance 15 |
| **News Data** | RapidAPI — Real-Time News Data |
| **Backend** | FastAPI + uvicorn |
| **Frontend** | Vanilla HTML / CSS / JS (no framework) |

## Agents

| # | Name | Responsibility |
|---|------|---------------|
| 1 | **Stock Agent** | Fetches prices for top 20 gainers and loser stocks for the day  |
| 2 | **Commodity Agent** | Fetches Gold, Silver, Crude Oil, Natural Gas, Copper prices |
| 3 | **ETF Agent** | Fetches SPY, QQQ, VTI, IWM, EEM, GLD, TLT, XLF, ARKK prices |
| 4 | **News Agent** | Searches 5 financial queries, pulls articles from the last week, generates research summary |
| 5 | **Validator Agent** | Checks system clock vs. data timestamps, scores freshness as HIGH / MEDIUM / LOW |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Source |
|----------|--------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| `RAPIDAPI_KEY` | [rapidapi.com](https://rapidapi.com/) — subscribe to **Yahoo Finance 15** and **Real-Time News Data** |
| `LANGCHAIN_API_KEY` | [smith.langchain.com](https://smith.langchain.com/) (optional, enables tracing) |

### 3. Run the server

```bash
python run.py
```

### 4. Open the dashboard

Navigate to **http://localhost:8000** in your browser.

Important:
- `0.0.0.0` is a bind address for the server, not a browser destination.
- If logs show `Uvicorn running on http://0.0.0.0:8000`, open `http://localhost:8000` (or `http://127.0.0.1:8000`).

---

## Deployment

### Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run:

```bash
python run.py
```

3. Open in browser:

```text
http://localhost:8000
```

Optional environment variables:
- `HOST` (default `0.0.0.0`)
- `PORT` (default `8000`)
- `RELOAD` (`true` to enable auto-reload)

### Hugging Face Spaces (Docker)

This repository is already configured for Docker Spaces:
- Docker startup uses `python run.py`.
- Container default is `PORT=7860` for Spaces compatibility.

Steps:
1. Create a new Space and select Docker SDK.
2. Connect this repository.
3. Add required secrets in Space Settings:
    - `OPENAI_API_KEY`
    - `RAPIDAPI_KEY`
    - `LANGCHAIN_API_KEY` (optional)
    - `APP_USERNAME` and `APP_PASSWORD` (recommended)
4. Deploy. Spaces will expose the app automatically on the Space URL.

### Railway

Railway works with this Docker setup because Railway injects a runtime `PORT`, and `run.py` reads it.

Steps:
1. Create a new Railway project from this GitHub repository.
2. Ensure the service is a Web Service.
3. Do not hardcode a port in Railway start command. Use Docker default command from the `Dockerfile`.
4. Set environment variables in Railway:
    - `OPENAI_API_KEY`
    - `RAPIDAPI_KEY`
    - `LANGCHAIN_API_KEY` (optional)
    - `APP_USERNAME` and `APP_PASSWORD`
5. Deploy and open the generated Railway domain.

If Railway shows "unexposed service":
- Confirm deployment logs include uvicorn startup.
- Confirm the app is listening on `0.0.0.0` and Railway-provided `PORT` (handled by current `run.py`).
- Confirm service type is Web Service.
- Redeploy after environment variable changes.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the frontend dashboard |
| `GET` | `/api/insights` | Runs the full 5-agent pipeline |
| `GET` | `/api/health` | Health check |

---

## LangSmith Tracing

When `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set, every LangGraph
invocation and every OpenAI call is automatically traced in LangSmith under the
project name specified by `LANGCHAIN_PROJECT` (default: `MarketInsights`).

---

## Project Structure

```
MarketInsights/
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── run.py                        # Uvicorn entry point
├── backend/
│   ├── config.py                 # Settings from .env
│   ├── state.py                  # LangGraph shared state
│   ├── graph.py                  # LangGraph workflow definition
│   ├── main.py                   # FastAPI application
│   ├── agents/
│   │   ├── stock_agent.py        # Agent 1
│   │   ├── commodity_agent.py    # Agent 2
│   │   ├── etf_agent.py          # Agent 3
│   │   ├── news_agent.py         # Agent 4
│   │   └── validator_agent.py    # Agent 5
│   └── services/
│       ├── yahoo_finance.py      # Yahoo Finance RapidAPI client
│       └── news_service.py       # Real-Time News RapidAPI client
└── frontend/
    ├── index.html                # Dashboard page
    ├── styles.css                # Dark-theme styles
    └── app.js                    # Fetch + render logic
```

---

## RapidAPI Setup

1. Create a free account at [rapidapi.com](https://rapidapi.com/)
2. Subscribe to these two APIs:
   - **[Yahoo Finance 15](https://rapidapi.com/sparior/api/yahoo-finance15)** — for stock/ETF/commodity quotes
   - **[Real-Time News Data](https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-news-data)** — for financial news
3. Copy your RapidAPI key into `.env`

> Both APIs offer free tiers sufficient for development and light usage.
