"""
Start the backend server.

    python main.py

Then open http://localhost:7860/api/health
"""

from pathlib import Path

import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent / "backend"

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        app_dir=str(BACKEND_DIR),         # where the "app" package lives
        reload=True,                      # restart automatically on code changes
        reload_dirs=[str(BACKEND_DIR)],
        port=7860,
    )
