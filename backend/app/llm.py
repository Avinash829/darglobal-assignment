"""
Talks to OpenRouter (OpenAI-compatible API) with automatic model fallback.

Free models are sometimes rate-limited, so we try each model in CHAT_MODELS
in order until one starts answering.
"""

from collections.abc import Iterator

from openai import OpenAI, OpenAIError

from app.config import CHAT_MODELS, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)


class AllModelsFailedError(Exception):
    pass


def stream_answer(messages: list[dict]) -> Iterator[str]:
    """Yield the answer text piece by piece from the first model that works."""
    errors = []
    for model in CHAT_MODELS:
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=0.2,          # low = factual, consistent answers
                max_tokens=900,
                extra_body={"reasoning": {"enabled": False}},  # faster replies
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except OpenAIError as error:
            print(f"Model {model} failed, trying next one: {error}")
            errors.append(f"{model}: {error}")
    raise AllModelsFailedError("; ".join(errors))
