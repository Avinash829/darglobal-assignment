"""All settings in one place. Values come from environment variables / .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
INDEX_DIR = PROJECT_ROOT / "data" / "index"
FRONTEND_BUILD_DIR = PROJECT_ROOT / "frontend" / "dist"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Free models, tried in order. If one is busy or down, the next one answers.
CHAT_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "inclusionai/ling-3.2-flash:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]

COLLECTION_NAME = "property_knowledge"
SEARCH_RESULTS_COUNT = 6          # knowledge chunks given to the model per question
EXAMPLE_LISTINGS_COUNT = 5        # Wasalt listings shown as examples per question
MAX_HISTORY_MESSAGES = 6          # previous chat turns sent with each question
CHUNK_SIZE_CHARS = 1200
