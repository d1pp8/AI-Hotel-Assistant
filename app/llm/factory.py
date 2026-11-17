from functools import lru_cache

from app.config import settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider

DEFAULT_MODELS = {"anthropic": "claude-opus-5-5"}

# Gemini exposes an OpenAI-compatible endpoint, so it reuses OpenAIProvider: no new class needed.
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    """Pick the provider from .env. The rest of the app only sees the LLMProvider interface."""
    provider = settings.LLM_PROVIDER
    model = settings.LLM_MODEL or DEFAULT_MODELS.get(provider)
    if not model:
        raise ValueError(f"LLM_MODEL must be set in .env for provider '{provider}'")

    match provider:
        case "anthropic":
            return AnthropicProvider(api_key=settings.API_KEY, model=model)
        case "openai":
            return OpenAIProvider(api_key=settings.API_KEY, model=model, base_url=settings.LLM_BASE_URL)
        case "gemini":
            return OpenAIProvider(
                api_key=settings.API_KEY, model=model, base_url=settings.LLM_BASE_URL or GEMINI_BASE_URL,
                name="Gemini",
            )
