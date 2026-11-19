"""Shared helpers for the scrapers: paths, polite delays and JSON saving."""

import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Identify ourselves honestly and keep the crawl slow.
USER_AGENT = "DarGlobalAssignmentBot/1.0 (candidate technical assessment, low-rate crawl)"
DELAY_BETWEEN_REQUESTS_SECONDS = 2.5


def polite_pause() -> None:
    """Wait between requests so we never put load on the target site."""
    time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)


def save_json(records: list | dict, file_name: str) -> Path:
    """Save records to data/raw/<file_name> and return the path."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DATA_DIR / file_name
    count = len(records) if isinstance(records, list) else 1
    indent = 2 if count < 1000 else None  # big files stay compact
    output_path.write_text(json.dumps(records, ensure_ascii=False, indent=indent), encoding="utf-8")
    print(f"Saved {count} records -> {output_path}")
    return output_path
