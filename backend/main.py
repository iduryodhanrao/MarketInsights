"""
FastAPI Application
───────────────────
Serves the market-insights REST API and the static frontend.

Endpoints:
  GET    /                 → serves frontend/index.html
  GET    /api/insights     → runs the full LangGraph pipeline (called on refresh)
  GET    /api/cached       → returns the last cached result (no API calls)
  GET    /api/health       → simple health-check
  GET    /api/watchlist     → list watchlist symbols
  POST   /api/watchlist     → add a symbol to the watchlist
  DELETE /api/watchlist     → remove a symbol from the watchlist
  GET    /api/recommendations → get latest buy/sell recommendations
"""

import asyncio
import os
import secrets
from datetime import datetime

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.graph import market_graph
from backend.state import MarketState
from backend.database import (
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    save_insights, get_cached_insights, get_recommendations,
)

app = FastAPI(title="Market Insights", version="2.0.0")

# ── HTTP Basic Auth ──────────────────────────────────────────────
security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Validate username + password against APP_USERNAME / APP_PASSWORD env vars."""
    ok_user = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        os.getenv("APP_USERNAME", "admin").encode("utf-8"),
    )
    ok_pass = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        os.getenv("APP_PASSWORD", "changeme123").encode("utf-8"),
    )
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

# ── CORS (allow local dev) ───────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve frontend static assets ────────────────────────────────
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ── Page routes ──────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    """Return the main dashboard HTML page."""
    return FileResponse("frontend/index.html")


# ── Health ───────────────────────────────────────────────────────

@app.get("/api/health", dependencies=[Depends(verify_credentials)])
async def health_check():
    """Lightweight health probe."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── Market insights (triggered on Refresh button only) ───────────

@app.get("/api/insights", dependencies=[Depends(verify_credentials)])
async def get_market_insights():
    """Run the full 6-agent LangGraph pipeline, cache results, and return them.

    This endpoint is intentionally expensive—it makes live API calls.
    The frontend should call /api/cached for initial page loads.
    """
    initial_state: MarketState = {
        "stocks": {},
        "commodities": {},
        "etfs": {},
        "news": {},
        "validation": {},
        "watchlist": {},
        "timestamp": datetime.now().isoformat(),
    }

    try:
        result = await asyncio.to_thread(market_graph.invoke, initial_state)
        serialised = _serialise(result)
        save_insights(serialised)
        return JSONResponse(content=serialised)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "timestamp": datetime.now().isoformat()},
        )


@app.get("/api/cached", dependencies=[Depends(verify_credentials)])
async def get_cached():
    """Return the most recently cached pipeline result without making API calls."""
    cached = get_cached_insights()
    if cached:
        return JSONResponse(content=cached)
    return JSONResponse(content={"empty": True, "message": "No cached data. Press Refresh to load."})


# ── Watchlist CRUD ───────────────────────────────────────────────

@app.get("/api/watchlist", dependencies=[Depends(verify_credentials)])
async def list_watchlist():
    """Return all symbols on the user's watchlist."""
    return JSONResponse(content={"watchlist": get_watchlist()})


@app.post("/api/watchlist", dependencies=[Depends(verify_credentials)])
async def add_symbol(request: Request):
    """Add a ticker symbol to the watchlist.  Body: { "symbol": "TICKER" }"""
    body = await request.json()
    symbol = body.get("symbol", "").strip().upper()
    if not symbol:
        return JSONResponse(status_code=400, content={"error": "symbol is required"})
    result = add_to_watchlist(symbol)
    return JSONResponse(content=result)


@app.delete("/api/watchlist", dependencies=[Depends(verify_credentials)])
async def delete_symbol(request: Request):
    """Remove a ticker symbol from the watchlist.  Body: { "symbol": "TICKER" }"""
    body = await request.json()
    symbol = body.get("symbol", "").strip().upper()
    if not symbol:
        return JSONResponse(status_code=400, content={"error": "symbol is required"})
    result = remove_from_watchlist(symbol)
    return JSONResponse(content=result)


# ── Recommendations ──────────────────────────────────────────────

@app.get("/api/recommendations", dependencies=[Depends(verify_credentials)])
async def list_recommendations():
    """Return latest buy/sell/hold recommendations for watchlist symbols."""
    return JSONResponse(content={"recommendations": get_recommendations()})


# ── Helpers ──────────────────────────────────────────────────────

def _serialise(obj):
    """Recursively convert non-serialisable values to strings."""
    if hasattr(obj, "items"):
        return {k: _serialise(v) for k, v in obj.items()}
    if hasattr(obj, "__iter__") and not hasattr(obj, "upper"):
        return [_serialise(i) for i in obj]
    try:
        import json
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)
