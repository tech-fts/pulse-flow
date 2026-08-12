from enum import StrEnum

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    PROJECT_NAME: str = "PulseFlow"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: SecretStr
    REDIS_URL: SecretStr
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    MAX_REQUEST_BYTES: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    WORKER_CONSUMER_PREFIX: str = "dispatch-worker"
    EVENT_STREAM_MAXLEN: int = Field(default=100_000, ge=1000)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if not self.CORS_ORIGINS or "*" in self.CORS_ORIGINS:
                raise ValueError("Use explicit CORS origins in production")
        return self


settings = Settings()
