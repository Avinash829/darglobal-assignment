"""
The chat pipeline. For every question:

  1. search      -> find relevant DarGlobal / Wasalt documents (vector search)
  2. filter      -> if the question asks for listings, filter Wasalt data exactly
  3. prompt      -> put the results into the prompt as CONTEXT
  4. generate    -> stream the answer from a free OpenRouter model

Only step 4 calls the LLM, so each question costs exactly one request.
"""

from collections.abc import Iterator

from app import knowledge_base, listings, llm
from app.config import MAX_HISTORY_MESSAGES
from app.prompts import SYSTEM_PROMPT, build_context


def asks_only_about_darglobal(question: str) -> bool:
    text = question.lower()
    mentions_darglobal = "darglobal" in text or "dar global" in text
    return mentions_darglobal and "wasalt" not in text


def describe_matching_listings(question: str) -> str:
    """Return a text summary of Wasalt listings matching the question, or ''."""
    if asks_only_about_darglobal(question):
        return ""
    filters = listings.parse_filters(question)
    if filters.is_empty():
        return ""

    total, examples = listings.find_listings(filters)
    lines = [f"[Wasalt] Listings matching ({filters.describe()}): {total} found."]
    for item in examples:
        details = ", ".join(
            f"{label}: {item[key]}" for label, key in
            [("bedrooms", "bedrooms"), ("area sqm", "area_sqm"), ("facing", "facing")] if item[key]
        )
        lines.append(f"- {item['title']} ({item['purpose']}; {details}) {item['url']}")
    return "\n".join(lines)


def answer_question(question: str, history: list[dict]) -> tuple[list[dict], Iterator[str]]:
    """Return (sources used, stream of answer text)."""
    documents = knowledge_base.search(question)
    listing_summary = describe_matching_listings(question)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history[-MAX_HISTORY_MESSAGES:],
        {"role": "user", "content": f"CONTEXT:\n{build_context(documents, listing_summary)}\n\nQUESTION: {question}"},
    ]

    sources = list({doc["url"]: {"title": doc["title"], "url": doc["url"], "source": doc["source"]}
                    for doc in documents}.values())
    return sources, llm.stream_answer(messages)
