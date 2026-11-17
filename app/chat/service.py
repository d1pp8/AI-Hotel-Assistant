import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import Conversation, Message
from app.llm.base import ChatMessage, LLMProvider
from app.rag.retrieval import SearchResult, search

HISTORY_LIMIT = 10  # last N messages sent to the LLM: enough context, bounded cost
TOP_K = 3

SYSTEM_PROMPT = """You are the virtual front-desk assistant of a hotel. You answer guests' questions \
using only the hotel information inside <knowledge_base>.

Rules:
- If the answer is not in the knowledge base, say honestly that you don't have this information \
and suggest contacting the reception. Never invent times, prices, or services.
- Language: detect the language of the guest's LATEST message and reply in exactly that language. \
The guest may switch languages mid-conversation; ignore the language of earlier messages \
and of the knowledge base (which is German).
- Be friendly and brief: 1-3 sentences, plain text without Markdown. Use the conversation history to understand follow-up questions.

<knowledge_base>
{context}
</knowledge_base>"""


class ConversationNotFound(Exception):
    pass


@dataclass
class ChatResult:
    conversation_id: uuid.UUID
    answer: str
    sources: list[SearchResult]


def _format_context(chunks: list[SearchResult]) -> str:
    return "\n".join(f'<entry id="{c.id}" title="{c.title}">{c.content}</entry>' for c in chunks)


async def _load_history(session: AsyncSession, conversation_id: uuid.UUID) -> list[ChatMessage]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(HISTORY_LIMIT)
    )
    rows = (await session.scalars(stmt)).all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


async def answer_question(
    session: AsyncSession,
    llm: LLMProvider,
    question: str,
    conversation_id: uuid.UUID | None = None,
) -> ChatResult:
    # 1. Find or start the conversation.
    if conversation_id is None:
        conversation = Conversation()
        session.add(conversation)
        await session.flush()  # sends INSERT so conversation.id exists; not committed yet
        history: list[ChatMessage] = []
    else:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationNotFound(conversation_id)
        history = await _load_history(session, conversation_id)

    # 2. Retrieve. Follow-ups like "und am Wochenende?" mean nothing on their own,
    #    so we search with the previous user question attached.
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    chunks = await search(session, f"{last_user} {question}".strip(), top_k=TOP_K)

    # 3. Generate.
    system = SYSTEM_PROMPT.format(context=_format_context(chunks))
    answer = await llm.generate(system, [*history, {"role": "user", "content": question}])

    # 4. Save both messages in one transaction, only after the LLM succeeded:
    #    a failed call leaves no half-written exchange in the history.
    session.add_all([
        Message(conversation_id=conversation.id, role="user", content=question),
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            sources=[c.id for c in chunks],
        ),
    ])
    await session.commit()

    return ChatResult(conversation_id=conversation.id, answer=answer, sources=chunks)


async def get_messages(session: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    if await session.get(Conversation, conversation_id) is None:
        raise ConversationNotFound(conversation_id)
    stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    return list((await session.scalars(stmt)).all())
