"""Smoke test for the configured LLM: `uv run python -m app.llm`."""

import asyncio

from app.config import settings
from app.llm.factory import get_llm


async def main() -> None:
    llm = get_llm()
    print(f"Provider: {settings.LLM_PROVIDER}, class: {type(llm).__name__}")
    answer = await llm.generate(
        system="You are a friendly hotel receptionist. Answer in one short sentence.",
        messages=[{"role": "user", "content": "Hallo! Wer bist du?"}],
    )
    print(f"Answer: {answer}")


if __name__ == "__main__":
    asyncio.run(main())
