from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.rag.embeddings import EMBEDDING_DIM


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(index=True)
    title: Mapped[str] = mapped_column()
    content: Mapped[str] = mapped_column()

    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
