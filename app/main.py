from fastapi import FastAPI

app = FastAPI(title="Hotel FAQ Assistant", version="0.0.1")

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
