from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DispatchOS / PulseFlow"
    API_V1_STR: str = "/api/v1"

    # ── PostgreSQL (resolves to Docker Compose service name) ──────
    POSTGRES_USER: str = "dispatch_user"
    POSTGRES_PASSWORD: str = "secure_random_db_password"
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "dispatch_os"

    # ── Redis (resolves to Docker Compose service name) ───────────
    REDIS_URL: str = "redis://redis:6379/0"

    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
