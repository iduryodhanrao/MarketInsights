"""
Application Entry Point
───────────────────────
Launches the FastAPI server via uvicorn.

Works for both local development and Railway:
- `PORT` is honoured when provided by the platform.
- `RELOAD=true` can be set locally for auto-reload.
"""

import os

import uvicorn


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Parse common boolean env-var values."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = _as_bool(os.getenv("RELOAD"), default=False)

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )
