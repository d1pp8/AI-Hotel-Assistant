FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/hf

WORKDIR /app

# 1. Dependencies first: this layer is cached until pyproject.toml / uv.lock change,
#    so editing the code doesn't reinstall PyTorch on every build.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# 2. Bake the embedding model into the image (same name as app/rag/embeddings.py):
#    the container starts without downloading anything.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
ENV HF_HUB_OFFLINE=1

# 3. Application code last: it changes most often.
COPY app ./app
COPY data ./data

# Don't run as root inside the container.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# Ingest is idempotent, so running it on every start keeps the DB in sync with the JSON file.
CMD ["sh", "-c", "python -m app.rag.ingest && fastapi run app/main.py --host 0.0.0.0 --port 8000"]
