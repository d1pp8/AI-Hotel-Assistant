from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    POSTGRES_HOST : str
    POSTGRES_PORT : int
    POSTGRES_USER : str
    POSTGRES_PASS : str
    POSTGRES_NAME : str

    LLM_PROVIDER : Literal["anthropic", "openai", "gemini"] = "anthropic"
    LLM_MODEL : str | None = None      # default per provider, see app/llm/factory.py
    LLM_BASE_URL : str | None = None   # OpenAI-compatible servers, e.g. Ollama: http://localhost:11434/v1
    API_KEY : str = ""

    DB_ECHO : bool = False  # True prints every SQL query, handy for debugging


    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASS}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True)


settings = Settings()