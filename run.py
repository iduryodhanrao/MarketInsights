"""
Application Entry Point
───────────────────────
Launches the FastAPI server via uvicorn with live-reload enabled.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
