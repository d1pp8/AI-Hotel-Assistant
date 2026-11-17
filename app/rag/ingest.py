import asyncio
import json

from sqlalchemy import delete, text

from app.config import BASE_DIR
from app.rag.embeddings import embed_passages
from app.db import Base, async_session, engine
from app.rag.models import KnowledgeChunk

KB_PATH = BASE_DIR / "data" / "knowledge_base.json"


async def ingest_data() -> None:
    items = json.loads(KB_PATH.read_text(encoding="utf-8"))

    # Embed title + content together: the title carries strong keywords ("Parkmöglichkeiten").
    embeddings = embed_passages([f"{i['title']}\n{i['content']}" for i in items])

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Full reload keeps the DB in sync with the JSON file (idempotent: safe to rerun).
        await session.execute(delete(KnowledgeChunk))
        session.add_all(
            KnowledgeChunk(
                id=item["id"],
                category=item["category"],
                title=item["title"],
                content=item["content"],
                embedding=vector,
            )
            for item, vector in zip(items, embeddings, strict=True)
        )
        await session.commit()

    print(f"Ingested {len(items)} chunks into knowledge_chunks")


if __name__ == "__main__":
    asyncio.run(ingest_data())
