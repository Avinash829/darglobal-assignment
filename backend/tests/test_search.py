"""
Retrieval quality checks: the right documents must come back for typical questions.
These run against the real index and use no LLM requests.
"""

import pytest

from app.chat import pick_sources
from app.knowledge_base import search


def titles_for(question: str) -> list[str]:
    return [doc["title"] for doc in search(question)]


@pytest.mark.parametrize("question, expected_title", [
    ("Tell me about DG1", "DG1"),
    ("When will Trump Tower Jeddah be completed?", "Trump Tower Jeddah"),
    ("Which DarGlobal residences are designed with Pagani?", "Da Vinci Tower, Interiors By Pagani"),
    ("Lamborghini branded villas", "Tierra Viva, Design inspired by Automobili Lamborghini"),
    ("Which areas in Jeddah have villas for sale on Wasalt?", "Wasalt properties in Jeddah"),
    ("Which DarGlobal projects are in Dubai?", "DarGlobal projects overview"),
])
def test_expected_document_is_found(question, expected_title):
    assert expected_title in titles_for(question)


def test_city_question_only_shows_that_city():
    sources = pick_sources(search("Which areas in Jeddah have villas for sale on Wasalt?"))
    wasalt_titles = [source["title"] for source in sources if source["source"] == "Wasalt"]
    assert wasalt_titles and all("Jeddah" in title for title in wasalt_titles)


def test_unrelated_documents_are_not_shown_as_sources():
    sources = pick_sources(search("What branded residences does DarGlobal have with Lamborghini?"))
    assert all(source["source"] == "DarGlobal" for source in sources)
