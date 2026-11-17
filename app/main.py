import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat import models as chat_models  # noqa: F401  (registers tables in Base.metadata)
from app.config import BASE_DIR
from app.chat.service import ConversationNotFound, answer_question, get_messages
from app.db import Base, engine, get_session
from app.llm.base import LLMError, LLMProvider
from app.llm.factory import get_llm
from app.rag import models as rag_models  # noqa: F401
from app.rag.embeddings import get_model
from app.rag.retrieval import search
from app.schemas import ChatRequest, ChatResponse, MessageOut, SearchHit, SearchRequest, Source


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Create missing tables. Fine for a demo; in production this is Alembic migrations' job.
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    get_model()  # warm up: load the embedding model at startup, not on the first request
    yield
    await engine.dispose()


app = FastAPI(title="Hotel FAQ Assistant", version="0.1.0", lifespan=lifespan)

STATIC_DIR = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SessionDep = Annotated[AsyncSession, Depends(get_session)]
# Injected, not imported directly: tests can swap in a fake LLM via app.dependency_overrides.
LLMDep = Annotated[LLMProvider, Depends(get_llm)]


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search")
async def search_knowledge(body: SearchRequest, session: SessionDep) -> list[SearchHit]:
    results = await search(session, body.query, top_k=body.top_k)
    return [SearchHit(**vars(r)) for r in results]


@app.post("/chat")
async def chat(body: ChatRequest, session: SessionDep, llm: LLMDep) -> ChatResponse:
    try:
        result = await answer_question(session, llm, body.message, body.conversation_id)
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except LLMError as e:
        # 502 Bad Gateway: our server is fine, the upstream LLM failed.
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(
        conversation_id=result.conversation_id,
        answer=result.answer,
        sources=[Source(id=s.id, title=s.title, score=s.score) for s in result.sources],
    )


@app.get("/conversations/{conversation_id}/messages")
async def conversation_messages(conversation_id: uuid.UUID, session: SessionDep) -> list[MessageOut]:
    try:
        messages = await get_messages(session, conversation_id)
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [MessageOut.model_validate(m) for m in messages]
