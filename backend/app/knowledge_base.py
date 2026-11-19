"""
The searchable knowledge base (RAG retrieval).

build_index()  turns the scraped JSON into text documents, embeds them and
               stores them in ChromaDB. Run once:  python -m app.knowledge_base
search()       finds the documents most similar to a question.

ChromaDB embeds the text itself with its built-in local model
(all-MiniLM-L6-v2), so no embedding API key is needed.
"""

import json
from collections import Counter, defaultdict

import chromadb

from app.config import (CHUNK_SIZE_CHARS, COLLECTION_NAME, INDEX_DIR,
                        RAW_DATA_DIR, SEARCH_RESULTS_COUNT)


def load_raw(file_name: str) -> list[dict]:
    return json.loads((RAW_DATA_DIR / file_name).read_text(encoding="utf-8"))


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> list[str]:
    """Split text on line breaks into chunks of about chunk_size characters."""
    chunks, current = [], ""
    for line in text.splitlines():
        if current and len(current) + len(line) > chunk_size:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current)
    return chunks


def darglobal_documents() -> list[dict]:
    documents = []
    for page in load_raw("darglobal_pages.json"):
        # A header with the key facts is added to every chunk, so each chunk
        # still makes sense on its own.
        header = f"DarGlobal page: {page['title']}\n"
        if page["page_type"] == "project":
            header += (f"Location: {page['location']} | Type: {page['property_type']} | "
                       f"Bedrooms: {page['bedrooms'] or 'see details'} | "
                       f"Completion: {page['completion_date'] or 'n/a'}\n")
        for chunk in split_into_chunks(page["text"]):
            documents.append({"text": header + chunk, "source": "DarGlobal",
                              "title": page["title"], "url": page["url"]})
    return documents


def darglobal_overview_document() -> dict:
    """One list of every project, so 'which projects are in X' questions see them all."""
    projects = [page for page in load_raw("darglobal_pages.json") if page["page_type"] == "project"]
    lines = [f"- {p['title']} | {p['location']} | {p['property_type']} | "
             f"completion: {p['completion_date'] or 'n/a'} | {p['url']}" for p in projects]
    text = (f"DarGlobal portfolio overview: all {len(projects)} projects "
            "(name | location | type | completion | link):\n" + "\n".join(lines))
    return {"text": text, "source": "DarGlobal", "title": "DarGlobal projects overview",
            "url": "https://darglobal.co.uk/projects"}


def wasalt_location_documents() -> list[dict]:
    """One document per location listing the property categories Wasalt covers there."""
    categories_by_location = defaultdict(list)
    for category in load_raw("wasalt_categories.json"):
        categories_by_location[category["location"]].append(category)

    documents = []
    for location, categories in categories_by_location.items():
        lines = [f"- {c['category']} for {c['purpose']}"
                 + (f" up to {c['max_price']}" if c.get("max_price") else "")
                 + f": {c['url']}" for c in categories]
        text = f"Wasalt property listings available in {location}, Saudi Arabia:\n" + "\n".join(lines)
        documents.append({"text": text, "source": "Wasalt",
                          "title": f"Properties in {location}", "url": categories[0]["url"]})
    return documents


def wasalt_overview_document() -> dict:
    """Totals per purpose and property type, so 'how many...' questions can be answered."""
    totals = Counter((item["purpose"], item["property_type"]) for item in load_raw("wasalt_listings.json"))
    lines = [f"- {property_type} for {purpose}: {count} listings"
             for (purpose, property_type), count in totals.most_common() if count >= 10]
    text = ("Wasalt (wasalt.sa) is a Saudi Arabian real estate platform. "
            "Overview of its public listings by purpose and property type:\n" + "\n".join(lines))
    return {"text": text, "source": "Wasalt", "title": "Wasalt listings overview", "url": "https://wasalt.sa/en"}


def get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    return client.get_or_create_collection(COLLECTION_NAME)


def build_index() -> None:
    documents = (darglobal_documents() + [darglobal_overview_document()]
                 + wasalt_location_documents() + [wasalt_overview_document()])
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)  # always rebuild from scratch
    collection = client.create_collection(COLLECTION_NAME)

    batch_size = 500
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        collection.add(
            ids=[f"doc-{start + i}" for i in range(len(batch))],
            documents=[doc["text"] for doc in batch],
            metadatas=[{"source": doc["source"], "title": doc["title"], "url": doc["url"]} for doc in batch],
        )
        print(f"Indexed {start + len(batch)}/{len(documents)}")


def results_per_source(question: str) -> dict[str, int]:
    """Give more results to the site the user is asking about."""
    text = question.lower()
    mentions_darglobal = "darglobal" in text or "dar global" in text
    mentions_wasalt = "wasalt" in text
    if mentions_darglobal and not mentions_wasalt:
        return {"DarGlobal": SEARCH_RESULTS_COUNT - 1, "Wasalt": 1}
    if mentions_wasalt and not mentions_darglobal:
        return {"DarGlobal": 1, "Wasalt": SEARCH_RESULTS_COUNT - 1}
    return {"DarGlobal": SEARCH_RESULTS_COUNT // 2, "Wasalt": SEARCH_RESULTS_COUNT // 2}


def search(question: str) -> list[dict]:
    """
    Return the most relevant documents: [{"text", "source", "title", "url"}].

    Each source is searched separately, so the ~3,000 Wasalt location documents
    cannot crowd out the smaller set of DarGlobal pages.
    """
    collection = get_collection()
    documents = []
    for source, result_count in results_per_source(question).items():
        results = collection.query(query_texts=[question], n_results=result_count,
                                   where={"source": source})
        documents += [{"text": text, **metadata}
                      for text, metadata in zip(results["documents"][0], results["metadatas"][0])]
    return documents


if __name__ == "__main__":
    build_index()
