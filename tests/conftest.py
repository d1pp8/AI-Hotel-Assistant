import asyncio
import os

import asyncpg
import pytest

# Must run before anything imports app.config: env vars override .env,
# so the whole app talks to a separate test database and never touches real data.
TEST_DB = "hotel_db_test"
os.environ["POSTGRES_NAME"] = TEST_DB

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.llm.base import ChatMessage, LLMError  # noqa: E402
from app.llm.factory import get_llm  # noqa: E402
from app.main import app  # noqa: E402
from app.rag.ingest import ingest_data  # noqa: E402


class FakeLLM:
    """Stands in for a real provider: free, instant, deterministic, and records what it was sent."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[ChatMessage]]] = []
        self.fail = False

    async def generate(self, system: str, messages: list[ChatMessage]) -> str:
        self.calls.append((system, messages))
        if self.fail:
            raise LLMError("fake outage")
        return "Fake answer"


async def _prepare_test_db() -> None:
    conn = await asyncpg.connect(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASS,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database="postgres",
    )
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB):
            await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await conn.close()

    await ingest_data()
    # Pooled connections belong to this event loop; TestClient runs its own loop.
    await engine.dispose()


@pytest.fixture(scope="session")
def client() -> TestClient:
    asyncio.run(_prepare_test_db())
    with TestClient(app) as c:  # runs the lifespan: creates chat tables, loads the model
        yield c


@pytest.fixture
def fake_llm() -> FakeLLM:
    fake = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: fake
    yield fake
    app.dependency_overrides.clear()
