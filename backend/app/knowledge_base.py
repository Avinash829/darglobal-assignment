"""
The searchable knowledge base (RAG retrieval).

build_index()  turns the scraped JSON into text documents, embeds them and
               stores them in ChromaDB. Run once:  python -m app.knowledge_base
search()       hybrid search: keyword (names) + vector (meaning).

ChromaDB embeds the text itself with its built-in local model
(all-MiniLM-L6-v2), so no embedding API key is needed.
"""

import json
import os
import re
from collections import Counter, defaultdict
from functools import cached_property, lru_cache

import chromadb
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from app.config import (CHUNK_SIZE_CHARS, COLLECTION_NAME, INDEX_DIR,
                        MAX_CONTEXT_DISTANCE, RAW_DATA_DIR, SEARCH_RESULTS_COUNT)

# Keyword search settings
MAX_KEYWORD_TITLES = 4           # pages added by name match per question
KEYWORD_RESULTS_PER_NAME = 2     # pages per matched word
KEYWORD_MATCH_DISTANCE = 0.3     # exact name matches count as highly relevant
WASALT_CITY_TITLE_PREFIX = "Wasalt properties in "

# Common words in page titles that are not names, so they are not used for keyword search.
GENERIC_TITLE_WORDS = {
    "the", "and", "for", "with", "dar", "darglobal", "global", "residences", "residence",
    "villas", "villa", "tower", "towers", "luxury", "branded", "living", "interiors", "by",
    "project", "projects", "real", "estate", "developer", "international", "hotel", "homes",
    "home", "second", "house", "brands", "portfolio", "dubai", "uae", "oman", "qatar", "spain",
    "saudi", "arabia", "london", "gulf", "about", "contact", "investor", "faq", "frequently",
    "asked", "questions", "commercial", "hospitality", "tokenization", "building", "communities",
    "apartments", "mansions", "plots", "penthouse", "downtown", "beach",
    # Wasalt city titles: "Wasalt properties in North Riyadh"
    "wasalt", "properties", "al", "an", "ar", "as", "ash", "ad", "north", "south", "east", "west",
    "central", "design", "inspired", "automobili", "trump", "park", "great", "escape",
}


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


def find_city(location: str, cities: set[str]) -> str:
    """'Jeddah Al Andalus' -> 'Jeddah' (the longest known city name the location starts with)."""
    matches = [city for city in cities if location == city or location.startswith(city + " ")]
    return max(matches, key=len) if matches else location


def wasalt_city_documents() -> list[dict]:
    """
    One document per city listing its districts per property category, e.g.
    'Villas for sale in Jeddah: Al Andalus, An Nada, ...'.
    A city is a location name that other locations start with ('Jeddah' -> 'Jeddah Al Andalus').
    """
    categories = load_raw("wasalt_categories.json")
    locations = {c["location"] for c in categories}
    cities = {loc for loc in locations if any(other.startswith(loc + " ") for other in locations)}
    cities = {city for city in cities if find_city(city, cities - {city}) == city}  # drop "Jeddah Industrial"

    districts = defaultdict(lambda: defaultdict(set))   # city -> "villas for sale" -> {districts}
    city_urls = {}
    for category in categories:
        if category.get("max_price"):
            continue
        city = find_city(category["location"], cities)
        if city not in cities:
            continue
        district = category["location"][len(city):].strip()
        group = f"{category['category']} for {category['purpose']}"
        if district:
            districts[city][group].add(district)
        elif category["category"] == "properties" or city not in city_urls:
            city_urls[city] = category["url"]

    documents = []
    for city, groups in districts.items():
        lines = [f"- {group.capitalize()} in {city}: {', '.join(sorted(names))}"
                 for group, names in sorted(groups.items(), key=lambda item: -len(item[1]))]
        text = f"Wasalt properties in {city}, Saudi Arabia. Districts with listings, by category:\n" + "\n".join(lines)
        documents.append({"text": text, "source": "Wasalt", "title": WASALT_CITY_TITLE_PREFIX + city,
                          "url": city_urls.get(city, "https://wasalt.sa/en")})
    return documents


def wasalt_overview_document() -> dict:
    """Totals per purpose and property type, so 'how many...' questions can be answered."""
    totals = Counter((item["purpose"], item["property_type"]) for item in load_raw("wasalt_listings.json"))
    lines = [f"- {property_type} for {purpose}: {count} listings"
             for (purpose, property_type), count in totals.most_common() if count >= 10]
    text = ("Wasalt (wasalt.sa) is a Saudi Arabian real estate platform. "
            "Overview of its public listings by purpose and property type:\n" + "\n".join(lines))
    return {"text": text, "source": "Wasalt", "title": "Wasalt listings overview", "url": "https://wasalt.sa/en"}


def build_index() -> None:
    documents = (darglobal_documents() + [darglobal_overview_document()]
                 + wasalt_city_documents() + wasalt_location_documents() + [wasalt_overview_document()])
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)  # always rebuild from scratch
    collection = client.create_collection(COLLECTION_NAME)

    batch_size = 200
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        texts = [doc["text"] for doc in batch]
        collection.add(
            ids=[f"doc-{start + i}" for i in range(len(batch))],
            documents=texts,
            embeddings=get_embedder()(texts),
            metadatas=[{"source": doc["source"], "title": doc["title"], "url": doc["url"]} for doc in batch],
        )
        print(f"Indexed {start + len(batch)}/{len(documents)}")


@lru_cache(maxsize=1)
def get_collection() -> chromadb.Collection:
    """Open the database once and reuse it (opening it per question is slow)."""
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    return client.get_collection(COLLECTION_NAME)


class LightweightEmbedder(ONNXMiniLM_L6_V2):
    """
    ChromaDB's local embedding model, limited to one CPU thread.

    By default ONNX Runtime starts one thread per CPU core of the *host* machine.
    On small cloud containers (a fraction of one CPU) those threads fight each
    other and a single embedding becomes very slow. One sentence needs one thread.
    """

    @cached_property
    def model(self):
        options = self.ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.log_severity_level = 3
        model_path = os.path.join(self.DOWNLOAD_PATH, self.EXTRACTED_FOLDER_NAME, "model.onnx")
        return self.ort.InferenceSession(model_path, providers=["CPUExecutionProvider"], sess_options=options)


@lru_cache(maxsize=1)
def get_embedder() -> LightweightEmbedder:
    """The same local model ChromaDB used to build the index, loaded once."""
    return LightweightEmbedder(preferred_providers=["CPUExecutionProvider"])


@lru_cache(maxsize=1)
def title_index() -> dict[str, list[tuple[str, str]]]:
    """
    Maps distinctive title words to the documents whose title contains them, e.g.
    "pagani" -> [("DarGlobal", "Da Vinci Tower, Interiors By Pagani"), ...]
    "jeddah" -> [("Wasalt", "Wasalt properties in Jeddah"), ("DarGlobal", "Trump Tower Jeddah")]
    Shorter titles come first, so the closest match wins.
    """
    stored = get_collection().get(include=["metadatas"])["metadatas"]
    titles = {(meta["source"], meta["title"]) for meta in stored
              if meta["source"] == "DarGlobal" or meta["title"].startswith(WASALT_CITY_TITLE_PREFIX)}

    index = defaultdict(list)
    for source, title in sorted(titles, key=lambda item: len(item[1])):
        for word in set(re.findall(r"[a-z0-9]{3,}", title.lower())):
            if word not in GENERIC_TITLE_WORDS:
                index[word].append((source, title))
    return index


def sources_for(question: str) -> set[str]:
    """Which sites the question is about (both if it does not say)."""
    text = question.lower()
    mentions_darglobal = "darglobal" in text or "dar global" in text
    mentions_wasalt = "wasalt" in text
    if mentions_darglobal and not mentions_wasalt:
        return {"DarGlobal"}
    if mentions_wasalt and not mentions_darglobal:
        return {"Wasalt"}
    return {"DarGlobal", "Wasalt"}


def results_per_source(question: str) -> dict[str, int]:
    """Give more results to the site the user is asking about."""
    sources = sources_for(question)
    if sources == {"DarGlobal"}:
        return {"DarGlobal": SEARCH_RESULTS_COUNT - 1, "Wasalt": 1}
    if sources == {"Wasalt"}:
        return {"DarGlobal": 1, "Wasalt": SEARCH_RESULTS_COUNT - 1}
    return {"DarGlobal": SEARCH_RESULTS_COUNT // 2, "Wasalt": SEARCH_RESULTS_COUNT // 2}


def vector_search(question: str) -> list[dict]:
    """Meaning-based search. Each source is searched separately, so the ~3,000
    Wasalt location documents cannot crowd out the smaller set of DarGlobal pages."""
    collection = get_collection()
    question_embedding = get_embedder()([question])  # embed once, reuse for every query
    documents = []
    for source, result_count in results_per_source(question).items():
        results = collection.query(query_embeddings=question_embedding, n_results=result_count,
                                   where={"source": source}, include=["documents", "metadatas", "distances"])
        for text, metadata, distance in zip(results["documents"][0], results["metadatas"][0],
                                            results["distances"][0]):
            if distance <= MAX_CONTEXT_DISTANCE:  # skip documents that are not really related
                documents.append({"text": text, **metadata, "distance": distance})
    return documents


def keyword_search(question: str) -> list[dict]:
    """
    Name search on titles: 'Pagani' finds 'Da Vinci Tower, Interiors By Pagani',
    'Jeddah' finds 'Wasalt properties in Jeddah'. Vector search can miss exact names.
    """
    index = title_index()
    allowed_sources = sources_for(question)
    question_words = dict.fromkeys(re.findall(r"[a-z0-9]+", question.lower()))  # unique, in order

    matched_titles = []
    for word in question_words:
        titles = [title for source, title in index.get(word, []) if source in allowed_sources]
        matched_titles += titles[:KEYWORD_RESULTS_PER_NAME]
    matched_titles = list(dict.fromkeys(matched_titles))[:MAX_KEYWORD_TITLES]

    documents = []
    for title in matched_titles:
        # The first chunk of a page holds its summary and key facts.
        result = get_collection().get(where={"title": title}, limit=1, include=["documents", "metadatas"])
        documents += [{"text": text, **metadata, "distance": KEYWORD_MATCH_DISTANCE}
                      for text, metadata in zip(result["documents"], result["metadatas"])]
    return documents


def search(question: str) -> list[dict]:
    """
    Hybrid search: keyword matches first, then vector matches, without duplicates.
    Returns [{"text", "source", "title", "url", "distance"}]; lower distance = more relevant.
    """
    keyword_documents = keyword_search(question)

    # If the question names a Saudi city, keep only Wasalt results from that city.
    named_cities = [doc["title"].removeprefix(WASALT_CITY_TITLE_PREFIX) for doc in keyword_documents
                    if doc["title"].startswith(WASALT_CITY_TITLE_PREFIX)]
    vector_documents = [doc for doc in vector_search(question)
                        if doc["source"] != "Wasalt" or not named_cities
                        or any(city in doc["title"] for city in named_cities)]

    documents, seen_texts = [], set()
    for document in keyword_documents + vector_documents:
        if document["text"] not in seen_texts:
            seen_texts.add(document["text"])
            documents.append(document)
    return documents


if __name__ == "__main__":
    build_index()
