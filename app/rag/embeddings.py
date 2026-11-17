from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    # Loading the model takes a few seconds, so we do it once per process.
    return SentenceTransformer(MODEL_NAME)


def embed_passages(texts: list[str]) -> list[list[float]]:
    # E5 models are trained with prefixes: "passage: " for documents, "query: " for questions.
    # Without them retrieval quality drops noticeably.
    vectors = get_model().encode([f"passage: {t}" for t in texts], normalize_embeddings=True)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    vector = get_model().encode(f"query: {text}", normalize_embeddings=True)
    return vector.tolist()
