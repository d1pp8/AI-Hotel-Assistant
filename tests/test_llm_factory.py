import pytest

from app.config import settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import GEMINI_BASE_URL, get_llm
from app.llm.openai_provider import OpenAIProvider


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    # Each test configures its own provider; monkeypatch restores settings afterwards.
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MODEL", None)
    monkeypatch.setattr(settings, "LLM_BASE_URL", None)
    get_llm.cache_clear()
    yield
    get_llm.cache_clear()


def test_anthropic_uses_default_model(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
    llm = get_llm()
    assert isinstance(llm, AnthropicProvider)
    assert llm._model == "claude-opus-5-5"


def test_gemini_reuses_openai_provider_with_google_url(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "LLM_MODEL", "gemini-2.5-flash")
    llm = get_llm()
    assert isinstance(llm, OpenAIProvider)
    assert str(llm._client.base_url) == GEMINI_BASE_URL


def test_openai_without_model_fails_fast(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    with pytest.raises(ValueError, match="LLM_MODEL must be set"):
        get_llm()
