from typing import Literal, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class LLMError(Exception):
    """Provider-agnostic error: the API layer only needs to know 'the LLM failed and why'."""


class LLMProvider(Protocol):
    """Anything with this method can be the bot's brain.

    Protocol = structural typing: providers don't inherit from a base class,
    they just implement `generate`. That keeps each provider file independent.
    """

    async def generate(self, system: str, messages: list[ChatMessage]) -> str: ...
