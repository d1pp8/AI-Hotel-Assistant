import anthropic

from app.llm.base import ChatMessage, LLMError

# Models that support server-side refusal fallbacks: if a safety classifier declines,
# the API re-runs the request on a fallback model inside the same call.
_FALLBACK_MODELS = {
    "claude-fable-5-2",
    "claude-fable-5-1",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
}

REFUSAL_TEXT = "Entschuldigung, dabei kann ich leider nicht helfen."


class AnthropicProvider:
    def __init__(self, api_key: str | None, model: str) -> None:
        # api_key=None lets the SDK fall back to ANTHROPIC_API_KEY / `ant auth login` profile.
        self._client = anthropic.AsyncAnthropic(api_key=api_key or None)
        self._model = model

    async def generate(self, system: str, messages: list[ChatMessage]) -> str:
        params = dict(
            model=self._model,
            max_tokens=16000,
            system=system,
            messages=messages,
            # FAQ answers are simple: low effort = faster and cheaper, quality holds for chat.
            output_config={"effort": "low"},
        )
        try:
            if self._model in _FALLBACK_MODELS:
                response = await self._client.beta.messages.create(
                    **params,
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                )
            else:
                response = await self._client.messages.create(**params)
        except anthropic.AuthenticationError as e:
            raise LLMError("Anthropic: invalid API key") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Anthropic: rate limited, try again later") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Anthropic API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Anthropic: network error") from e

        # Always check stop_reason before reading content.
        if response.stop_reason == "refusal":
            return REFUSAL_TEXT
        # content is a list of blocks (thinking, text, ...): keep only the text.
        return "".join(block.text for block in response.content if block.type == "text")
