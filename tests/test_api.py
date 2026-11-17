import uuid

import pytest


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_index_serves_chat_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Hotel Assistant" in response.text


@pytest.mark.parametrize(
    ("query", "expected_id"),
    [
        ("Wo kann ich parken?", "kb_003"),
        ("Во сколько завтрак?", "kb_004"),  # Russian question, German knowledge base
        ("Can I check out late?", "kb_002"),
    ],
)
def test_search_ranks_relevant_chunk_first(client, query, expected_id):
    hits = client.post("/search", json={"query": query}).json()
    assert hits[0]["id"] == expected_id
    assert hits == sorted(hits, key=lambda h: h["score"], reverse=True)


def test_chat_starts_conversation_and_grounds_prompt(client, fake_llm):
    response = client.post("/chat", json={"message": "Wo kann ich parken?"})

    assert response.status_code == 200
    data = response.json()
    uuid.UUID(data["conversation_id"])  # valid UUID
    assert data["answer"] == "Fake answer"
    assert data["sources"][0]["id"] == "kb_003"

    system, messages = fake_llm.calls[0]
    assert "15 Euro pro Tag" in system  # the retrieved chunk reached the LLM
    assert messages == [{"role": "user", "content": "Wo kann ich parken?"}]


def test_follow_up_gets_history_and_right_context(client, fake_llm):
    first = client.post("/chat", json={"message": "Wann gibt es Frühstück?"}).json()
    second = client.post(
        "/chat",
        json={"message": "Und am Wochenende?", "conversation_id": first["conversation_id"]},
    ).json()

    # "Und am Wochenende?" alone means nothing; with the previous question attached
    # retrieval still finds the breakfast entry.
    assert second["sources"][0]["id"] == "kb_004"

    _, messages = fake_llm.calls[1]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[-1]["content"] == "Und am Wochenende?"


def test_history_endpoint_returns_messages_in_order(client, fake_llm):
    cid = client.post("/chat", json={"message": "Hallo"}).json()["conversation_id"]
    client.post("/chat", json={"message": "Wo kann ich parken?", "conversation_id": cid})

    history = client.get(f"/conversations/{cid}/messages").json()

    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]
    assert history[0]["content"] == "Hallo"


def test_unknown_conversation_returns_404(client, fake_llm):
    unknown = str(uuid.uuid4())
    assert client.post("/chat", json={"message": "Hi", "conversation_id": unknown}).status_code == 404
    assert client.get(f"/conversations/{unknown}/messages").status_code == 404


@pytest.mark.parametrize("body", [{"message": ""}, {"message": "x" * 1001}, {}])
def test_invalid_request_returns_422(client, fake_llm, body):
    assert client.post("/chat", json=body).status_code == 422


def test_llm_failure_returns_502_and_saves_nothing(client, fake_llm):
    cid = client.post("/chat", json={"message": "Hallo"}).json()["conversation_id"]

    fake_llm.fail = True
    response = client.post("/chat", json={"message": "Wo kann ich parken?", "conversation_id": cid})

    assert response.status_code == 502
    assert "fake outage" in response.json()["detail"]
    # The failed exchange must not leave a dangling user message in the history.
    assert len(client.get(f"/conversations/{cid}/messages").json()) == 2
