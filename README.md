# DarGlobal & Wasalt Property Assistant

An AI chatbot that answers questions about **DarGlobal** luxury developments and
**Wasalt** property listings, using only publicly available data from both sites.

**Live demo:** _link added after deployment_

## Try asking

- Which DarGlobal projects are in Dubai?
- Tell me about Trump Tower Jeddah. When will it be completed?
- What branded residences does DarGlobal have with Lamborghini or Pagani?
- Show me 3 bedroom apartments for rent on Wasalt
- What areas in Jeddah have villas for sale on Wasalt?
- How many land plots are for sale on Wasalt?

## How it works

```
                 ┌──────────────── one-time, offline ────────────────┐
 darglobal.co.uk ─► scraper/darglobal.py (Playwright) ─┐
                                                       ├─► data/raw/*.json ─► knowledge_base.py ─► ChromaDB index
 wasalt.sa sitemaps ─► scraper/wasalt.py ──────────────┘                     (chunk + embed)
                 └───────────────────────────────────────────────────┘

 User ─► React UI ─► POST /api/chat (FastAPI)
                        │
                        ├─ 1. search    : vector search in ChromaDB (DarGlobal + Wasalt docs)
                        ├─ 2. filter    : exact Wasalt listing filter (type, purpose, bedrooms, size)
                        ├─ 3. prompt    : results become the CONTEXT of the prompt
                        └─ 4. generate  : free OpenRouter model, streamed back word by word
                                          (falls back to the next model if one is busy)
```

**Only step 4 calls the LLM, so every question costs exactly one request.** This matters
because free OpenRouter models have a daily request limit.

## Tech stack

| Part | Technology |
|---|---|
| Scraping | Python, Playwright (headless Chromium), sitemap parsing |
| Retrieval | ChromaDB with its built-in local embedding model (all-MiniLM-L6-v2) |
| LLM | OpenRouter free models: Nemotron 3.5 Super, Ling 3.2 Flash, Nemotron 3 Ultra (automatic fallback) |
| Backend | FastAPI, Server-Sent Events streaming |
| Frontend | React (Vite), react-markdown |
| Deployment | Docker (multi-stage build) on Render |

## Data collected

| Source | What | How |
|---|---|---|
| DarGlobal | 38 projects (location, type, completion date, full page text, FAQs) and 18 company / partner pages | Playwright renders each page; project cards come from the page's Next.js data |
| Wasalt | 62,695 listings (purpose, type, bedrooms, size, facing) and 13,688 city / district / price-band category pages | Parsed from the public sitemaps listed in wasalt.sa/robots.txt |

### Responsible scraping

- Only public pages, at a slow rate (2.5 seconds between requests), with an honest user agent.
- **Wasalt listing pages are protected by a Cloudflare bot check. We respected it and did not try
  to bypass it.** Instead we used the sitemaps Wasalt publishes for crawlers. The trade-off: no
  per-listing prices or exact city, which the bot tells users openly.
- No phone numbers or contact details are collected, in line with wasalt.sa/llms.txt.

## Project structure

```
scraper/
  common.py          paths, polite delay, JSON saving
  darglobal.py       DarGlobal projects + company pages
  wasalt.py          Wasalt sitemap parser
backend/app/
  config.py          all settings (models, paths, sizes)
  knowledge_base.py  builds the ChromaDB index and searches it
  listings.py        exact filtering of Wasalt listings
  prompts.py         system prompt and context builder
  llm.py             OpenRouter client with model fallback
  chat.py            the 4-step pipeline
  main.py            FastAPI routes
frontend/src/
  api/chatApi.js     reads the streamed answer
  hooks/useChat.js   conversation state + saved history
  utils/chatStorage.js  saves chats in the browser (localStorage)
  components/        WelcomeMessage, MessageBubble, ChatInput, HistoryPanel
Dockerfile
```

## Run locally

```bash
# 1. Python setup
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install -r backend/requirements.txt playwright
python -m playwright install chromium

# 2. Add your key
echo OPENROUTER_API_KEY=sk-or-v1-... > .env

# 3. (Optional) refresh the data and the index
python -m scraper.darglobal
python -m scraper.wasalt
cd backend && python -m app.knowledge_base

# 4. Start the API (project root) and the UI (from frontend/)
python main.py
npm install && npm run dev
```

### With Docker

```bash
docker build -t property-assistant .
docker run -p 7860:7860 --env-file .env property-assistant
# open http://localhost:7860
```

## Design decisions

- **Hybrid retrieval instead of pure vector search.** Vector search is good for "tell me about X",
  but bad at exact conditions like "3 bedrooms, for rent". Those are read from the question with
  simple rules and filtered in Python.
- **Per-source search.** Wasalt has about 3,000 location documents and DarGlobal about 300 chunks,
  so each source is searched separately to stop one from crowding out the other.
- **Overview documents.** One document lists every DarGlobal project and one summarises Wasalt
  listing counts, so questions like "which projects are in Dubai" see the full list.
- **Grounded answers.** The system prompt allows answers only from the retrieved context.
- **Prebuilt index.** The index is built once and shipped in the image, so the app starts fast and
  never scrapes at runtime.

## Possible improvements

- Use an LLM tool-calling agent to choose filters when a paid model with a higher rate limit is available
- Add per-listing prices and cities with an official Wasalt data feed or partnership
- Schedule a nightly scrape and re-index
- Add an evaluation set of questions and expected answers
