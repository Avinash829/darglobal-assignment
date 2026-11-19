"""
Exact filtering over Wasalt listings.

Vector search is good for "tell me about X" questions but bad at exact
conditions like "3-bedroom apartments for rent". For those we read the
filters straight from the question with simple rules and filter the data
in Python. This costs no LLM call.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from app.config import EXAMPLE_LISTINGS_COUNT, RAW_DATA_DIR

# Words a user might type -> the property_type value stored in the data.
PROPERTY_TYPE_WORDS = {
    "apartment": "apartment", "flat": "apartment", "villa": "villa", "land": "land",
    "plot": "land", "floor": "floor", "building": "building", "rest house": "rest house",
    "chalet": "chalet", "studio": "studio", "room": "room", "farm": "farm",
}


@dataclass
class ListingFilters:
    purpose: str | None = None         # "sale", "rent" or "daily rental"
    property_type: str | None = None
    bedrooms: int | None = None
    min_area_sqm: int | None = None
    max_area_sqm: int | None = None

    def is_empty(self) -> bool:
        return self.purpose is None and self.property_type is None and self.bedrooms is None

    def describe(self) -> str:
        parts = [f"{name}={value}" for name, value in vars(self).items() if value is not None]
        return ", ".join(parts)


@lru_cache(maxsize=1)
def load_listings() -> list[dict]:
    """Load all listings once and keep them in memory."""
    return json.loads((RAW_DATA_DIR / "wasalt_listings.json").read_text(encoding="utf-8"))


def parse_filters(question: str) -> ListingFilters:
    """Read filters like purpose, type, bedrooms and size from a question."""
    text = question.lower()
    filters = ListingFilters()

    if re.search(r"daily|per night|booking|holiday", text):
        filters.purpose = "daily rental"
    elif re.search(r"\b(rent|rental|lease)\b", text):
        filters.purpose = "rent"
    elif re.search(r"\b(buy|sale|purchase)\b", text):
        filters.purpose = "sale"

    for word, property_type in PROPERTY_TYPE_WORDS.items():
        if re.search(rf"\b{word}s?\b", text):
            filters.property_type = property_type
            break

    bedrooms = re.search(r"(\d+)\s*(?:-\s*)?(?:bed|bedroom|bhk|br)\b", text)
    if bedrooms:
        filters.bedrooms = int(bedrooms.group(1))

    min_area = re.search(r"(?:over|above|more than|at least|min(?:imum)?)\s*(\d+)\s*(?:sqm|m2|square)", text)
    max_area = re.search(r"(?:under|below|less than|up to|max(?:imum)?)\s*(\d+)\s*(?:sqm|m2|square)", text)
    filters.min_area_sqm = int(min_area.group(1)) if min_area else None
    filters.max_area_sqm = int(max_area.group(1)) if max_area else None
    return filters


def matches(listing: dict, filters: ListingFilters) -> bool:
    if filters.purpose and listing["purpose"] != filters.purpose:
        return False
    if filters.property_type and filters.property_type not in (listing["property_type"] or ""):
        return False
    if filters.bedrooms and listing["bedrooms"] != filters.bedrooms:
        return False
    area = listing["area_sqm"]
    if filters.min_area_sqm and (area is None or area < filters.min_area_sqm):
        return False
    if filters.max_area_sqm and (area is None or area > filters.max_area_sqm):
        return False
    return True


def find_listings(filters: ListingFilters) -> tuple[int, list[dict]]:
    """Return (total number of matches, newest few matches as examples)."""
    matching = [listing for listing in load_listings() if matches(listing, filters)]
    matching.sort(key=lambda listing: listing.get("last_modified") or "", reverse=True)
    return len(matching), matching[:EXAMPLE_LISTINGS_COUNT]
