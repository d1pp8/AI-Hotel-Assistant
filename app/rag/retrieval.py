from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import embed_query
from app.rag.models import KnowledgeChunk


@dataclass
class SearchResult:
    id: str
    category: str
    title: str
    content: str
    score: float  # cosine similarity: 1.0 = identical meaning, ~0 = unrelated


async def search(
    session: AsyncSession,
    query: str,
    top_k: int = 3,
    min_score: float = 0.0,
) -> list[SearchResult]:
    query_vector = embed_query(query)

    # pgvector's "<=>" operator = cosine distance; similarity = 1 - distance.
    # ORDER BY distance lets Postgres use a vector index (HNSW) once the table grows.
    distance = KnowledgeChunk.embedding.cosine_distance(query_vector).label("distance")
    stmt = select(KnowledgeChunk, distance).order_by(distance).limit(top_k)

    rows = (await session.execute(stmt)).all()
    results = [
        SearchResult(
            id=chunk.id,
            category=chunk.category,
            title=chunk.title,
            content=chunk.content,
            score=round(1 - dist, 4),
        )
        for chunk, dist in rows
    ]
    return [r for r in results if r.score >= min_score]
