# DarGlobal & Wasalt Property Assistant

[![CI](https://github.com/Avinash829/darglobal-assignment/actions/workflows/ci.yml/badge.svg)](https://github.com/Avinash829/darglobal-assignment/actions/workflows/ci.yml)

An AI chatbot that answers questions about **DarGlobal** luxury developments and
**Wasalt** property listings in Saudi Arabia, using only publicly available data from both sites.

### Live demo: https://darglobal-assignment-829.onrender.com

## Try asking

- Which DarGlobal projects are in Dubai?
- When will Trump Tower Jeddah be completed?
- What branded residences does DarGlobal have with Lamborghini or Pagani?
- Show me 3 bedroom apartments for rent on Wasalt
- Which areas in Jeddah have villas for sale on Wasalt?
- What is the price of a 2 bedroom apartment in W Residences? *(the bot says it doesn't have prices instead of inventing one)*

## How it works

```
                 ┌──────────────────── one-time, offline ────────────────────┐
 darglobal.co.uk ─► scraper/darglobal.py (Playwright) ─┐
                                                       ├─► data/raw/*.json ─► knowledge_base.py ─► ChromaDB index
 wasalt.sa sitemaps ─► scraper/wasalt.py ──────────────┘                     (chunk + embed locally)
                 └───────────────────────────────────────────────────────────┘

 User ─► React UI ─► POST /api/chat (FastAPI)
                        │
                        ├─ 0. cache     : same question asked before? answer instantly, no LLM call
                        ├─ 1. search    : hybrid search in ChromaDB
                        │                   keyword match on project / city names  (exact)
                        │                 + vector search per source                (meaning)
                        │                 + relevance cut-off on vector distance
                        ├─ 2. filter    : exact Wasalt listing filter (purpose, type, bedrooms, size)
                        ├─ 3. prompt    : results become the CONTEXT of a grounded prompt
                        └─ 4. generate  : free OpenRouter model, streamed back word by word (SSE)
                                          falls back to the next model if one is busy
```

**Only step 4 calls the LLM, so each question costs at most one request**, and repeated
questions cost none. This matters because free OpenRouter models have a daily request limit.

## Tech stack

| Part | Technology |
|---|---|
| Scraping | Python, Playwright (headless Chromium), sitemap parsing |
| Retrieval | ChromaDB + local embedding model (all-MiniLM-L6-v2, ONNX), keyword search on titles |
| LLM | OpenRouter free models: Nemotron 3.5 Super → Ling 3.2 Flash → Nemotron 3 Ultra (automatic fallback) |
| Backend | FastAPI, Server-Sent Events streaming, answer cache |
| Frontend | React (Vite), react-markdown + GFM tables, chat history in localStorage |
| Quality | pytest (parsers, filters, retrieval quality), ESLint, GitHub Actions CI |
| Deployment | Docker (multi-stage build) on Render, kept awake by a scheduled GitHub Action |

## Data collected

| Source | What | How |
|---|---|---|
| DarGlobal | 38 projects (location, type, completion date, full page text, FAQs) and 18 company / partner pages | Playwright renders each page; project cards come from the page's Next.js data |
| Wasalt | 62,695 listings (purpose, type, bedrooms, size, facing) and 13,688 city / district / price-band category pages | Parsed from the public sitemaps listed in wasalt.sa/robots.txt |

The knowledge base holds **1,689 documents**: DarGlobal page chunks, a DarGlobal portfolio overview,
31 Wasalt city overviews, about 1,400 Wasalt district documents and a Wasalt listings overview.

### Responsible scraping

- Only public pages, at a slow rate (2.5 seconds between requests), with an honest user agent.
- **Wasalt listing pages are protected by a Cloudflare bot check. I respected it and did not try
  to bypass it.** Instead I used the sitemaps Wasalt publishes for crawlers. The trade-off: no
  per-listing prices or exact city per listing, which the bot tells users openly.
- No phone numbers or contact details are collected, in line with wasalt.sa/llms.txt.

## Design decisions

- **Hybrid retrieval.** Vector search understands meaning ("pool" ≈ "infinity pool") but can miss
  exact names: for "Lamborghini or Pagani" it returned only Lamborghini pages. A keyword match on
  project and city titles fixes this, and an exact Python filter handles conditions like
  "3 bedrooms, for rent, over 500 sqm" that vector search cannot.
- **Relevance cut-off.** Measured on this data, related documents score a vector distance below
  ~0.8 and unrelated ones above ~1.1. Documents above 1.0 are not given to the model, and only
  documents below 0.7 are shown as source links, so users never see irrelevant sources.
- **Per-source search.** Wasalt has ~1,400 district documents and DarGlobal ~220 chunks, so each
  source is searched separately so one cannot crowd out the other. If a question names a Saudi
  city, only that city's Wasalt documents are kept.
- **Overview documents.** A DarGlobal portfolio list and Wasalt city overviews let "which projects
  are in Dubai" or "which areas in Jeddah" questions see the complete picture.
- **Grounded answers.** The system prompt allows answers only from the retrieved context, with
  low temperature and links to the original pages.
- **One LLM call per question + answer cache.** Fits the free tier and keeps answers fast.
- **Prebuilt index, warm start.** The index ships inside the image, and the embedding model,
  index and listings are loaded at startup, so the first user does not wait.

### Performance work

| Step | Before | After | Fix |
|---|---|---|---|
| Search per question | ~2,500 ms | **~45 ms** | Embedding model loaded once and reused (it was being re-created on every call), database client cached |
| Index build | ~10 min | **~1 min** | Same fix during indexing |
| Repeated question | 1 LLM call | **0 calls, instant** | Answer cache |

## Project structure

```
scraper/
  common.py            paths, polite delay, JSON saving
  darglobal.py         DarGlobal projects + company pages
  wasalt.py            Wasalt sitemap parser
backend/app/
  config.py            all settings (models, thresholds, sizes)
  knowledge_base.py    builds the ChromaDB index; hybrid search
  listings.py          exact filtering of Wasalt listings
  prompts.py           system prompt and context builder
  llm.py               OpenRouter client with model fallback
  chat.py              the pipeline: cache → search → filter → prompt → generate
  main.py              FastAPI routes, startup warm-up
backend/tests/         parser, filter and retrieval-quality tests
frontend/src/
  api/chatApi.js       reads the streamed answer
  hooks/useChat.js     conversation state + saved history
  utils/chatStorage.js saves chats in the browser (localStorage)
  components/          WelcomeMessage, MessageBubble, ChatInput, HistoryPanel
Dockerfile             multi-stage: build React, then serve it from FastAPI
.github/workflows/     CI (tests, lint, build) and keep-awake ping
```

## Run locally

```bash
# 1. Python setup
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install -r backend/requirements.txt

# 2. Add your key
echo OPENROUTER_API_KEY=sk-or-v1-... > .env

# 3. Start the API (project root) and the UI (from frontend/)
python main.py
cd frontend && npm install && npm run dev               # http://localhost:5173
```

Refresh the data and the index (optional):

```bash
pip install playwright && python -m playwright install chromium
python -m scraper.darglobal
python -m scraper.wasalt
cd backend && python -m app.knowledge_base
```

Run the tests:

```bash
pip install pytest
cd backend && python -m pytest -q
```

### With Docker

```bash
docker build -t property-assistant .
docker run -p 7860:7860 --env-file .env property-assistant
# open http://localhost:7860
```

## Possible improvements

- Use a tool-calling agent to choose filters once a paid model with a higher rate limit is available
- Add per-listing prices and cities through an official Wasalt data feed or partnership
- Schedule a nightly scrape and re-index
- Add a reranker and an answer-quality evaluation set (LLM-as-judge)
