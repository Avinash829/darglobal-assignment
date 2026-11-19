"""
The chat pipeline. For every question:

  1. search      -> hybrid search for DarGlobal / Wasalt documents (keyword + vector)
  2. filter      -> if the question asks for listings, filter Wasalt data exactly
  3. prompt      -> put the results into the prompt as CONTEXT
  4. generate    -> stream the answer from a free OpenRouter model

Only step 4 calls the LLM, so each question costs at most one request.
Repeated questions (without chat history) are answered from a cache: zero requests.
"""

from collections import OrderedDict
from collections.abc import Iterator

from app import knowledge_base, listings, llm
from app.config import (ANSWER_CACHE_SIZE, MAX_HISTORY_MESSAGES, MAX_SOURCE_DISTANCE,
                        MAX_SOURCE_LINKS)
from app.prompts import SYSTEM_PROMPT, build_context

# question -> (sources, answer). OrderedDict lets us drop the oldest entry when full.
answer_cache: OrderedDict[str, tuple[list[dict], str]] = OrderedDict()


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


def pick_sources(documents: list[dict]) -> list[dict]:
    """Links shown under the answer: only clearly relevant documents, one per URL."""
    sources = {}
    for doc in sorted(documents, key=lambda doc: doc["distance"]):  # most relevant first
        if doc["distance"] <= MAX_SOURCE_DISTANCE and doc["url"] not in sources:
            sources[doc["url"]] = {"title": doc["title"], "url": doc["url"], "source": doc["source"]}
    return list(sources.values())[:MAX_SOURCE_LINKS]


def cache_key(question: str) -> str:
    return " ".join(question.lower().split()).rstrip("?.! ")


def remember_answer(key: str, sources: list[dict], answer_stream: Iterator[str]) -> Iterator[str]:
    """Pass the answer through to the user, and cache it once it has fully arrived."""
    answer = ""
    for text_piece in answer_stream:
        answer += text_piece
        yield text_piece
    answer_cache[key] = (sources, answer)
    if len(answer_cache) > ANSWER_CACHE_SIZE:
        answer_cache.popitem(last=False)


def answer_question(question: str, history: list[dict]) -> tuple[list[dict], Iterator[str]]:
    """Return (sources used, stream of answer text)."""
    key = cache_key(question)
    if not history and key in answer_cache:  # same question asked before: no LLM call
        sources, answer = answer_cache[key]
        return sources, iter([answer])

    documents = knowledge_base.search(question)
    listing_summary = describe_matching_listings(question)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history[-MAX_HISTORY_MESSAGES:],
        {"role": "user", "content": f"CONTEXT:\n{build_context(documents, listing_summary)}\n\nQUESTION: {question}"},
    ]

    sources = pick_sources(documents)
    answer_stream = llm.stream_answer(messages)
    if not history:  # answers that depend on earlier messages are not cached
        answer_stream = remember_answer(key, sources, answer_stream)
    return sources, answer_stream
