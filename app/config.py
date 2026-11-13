from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    POSTGRES_HOST : str
    POSTGRES_PORT : int
    POSTGRES_USER : str
    POSTGRES_PASS : str
    POSTGRES_NAME : str

    LLM_PROVIDER : str
    API_KEY : str


    @property
    def DATABASE_ASYNGPH_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASS}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()