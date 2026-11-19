"""Make the `app` package (backend/) and the `scraper` package (project root) importable in tests."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND_DIR), str(BACKEND_DIR.parent)]
