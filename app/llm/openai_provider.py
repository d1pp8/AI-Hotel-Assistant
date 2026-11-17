import openai

from app.llm.base import ChatMessage, LLMError


class OpenAIProvider:
    """OpenAI Chat Completions API.

    Also works with any OpenAI-compatible server (Ollama, vLLM, LM Studio)
    by setting LLM_BASE_URL, e.g. http://localhost:11434/v1 for Ollama.
    """

    def __init__(
        self, api_key: str | None, model: str, base_url: str | None = None, name: str = "OpenAI"
    ) -> None:
        # Local servers like Ollama ignore the key, but the SDK requires a non-empty one.
        self._client = openai.AsyncOpenAI(api_key=api_key or "not-needed", base_url=base_url)
        self._model = model
        self._name = name  # used in error messages: "Gemini", "Ollama", ...

    async def generate(self, system: str, messages: list[ChatMessage]) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                # OpenAI has no separate system field: it's the first message.
                messages=[{"role": "system", "content": system}, *messages],
            )
        except openai.AuthenticationError as e:
            raise LLMError(f"{self._name}: invalid API key") from e
        except openai.RateLimitError as e:
            raise LLMError(f"{self._name}: rate limited, try again later") from e
        except openai.APIStatusError as e:
            raise LLMError(f"{self._name} API error {e.status_code}: {e.message}") from e
        except openai.APIConnectionError as e:
            raise LLMError(f"{self._name}: network error (is the server at LLM_BASE_URL running?)") from e

        return response.choices[0].message.content or ""
