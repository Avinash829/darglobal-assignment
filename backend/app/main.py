"""
FastAPI server.

  GET  /api/health  -> simple status check
  POST /api/chat    -> streams the answer as Server-Sent Events (SSE)
  GET  /            -> the built React app

Run locally:  uvicorn app.main:app --reload --port 7860   (from the backend/ folder)
"""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import knowledge_base, listings
from app.chat import answer_question
from app.config import FRONTEND_BUILD_DIR
from app.llm import AllModelsFailedError


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load the embedding model, the vector index and the listings once at startup,
    so the first user does not wait for them."""
    knowledge_base.search("warm up")
    listings.load_listings()
    yield


app = FastAPI(title="DarGlobal & Wasalt Property Assistant", lifespan=lifespan)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[ChatMessage] = []


def sse_event(event_type: str, data) -> str:
    """Format one Server-Sent Event."""
    return f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    history = [message.model_dump() for message in request.history]
    sources, answer_stream = answer_question(request.question, history)

    def event_stream():
        yield sse_event("sources", sources)
        try:
            for text_piece in answer_stream:
                yield sse_event("token", text_piece)
        except AllModelsFailedError:
            yield sse_event("error", "All free AI models are busy right now. Please try again in a minute.")
        yield sse_event("done", None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Serve the React build last, so /api routes take priority.
if FRONTEND_BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="frontend")
