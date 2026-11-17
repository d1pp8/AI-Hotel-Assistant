"""Request/response models of the HTTP API (what clients see), separate from DB models."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500, examples=["Wo kann ich parken?"])
    top_k: int = Field(default=3, ge=1, le=10)


class SearchHit(BaseModel):
    id: str
    category: str
    title: str
    content: str
    score: float


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000, examples=["Wann gibt es Frühstück?"])
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Omit to start a new conversation; send it back to continue one."
    )


class Source(BaseModel):
    id: str
    title: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    sources: list[Source]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # build directly from the SQLAlchemy object

    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
