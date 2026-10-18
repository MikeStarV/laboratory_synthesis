from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


LABORATORY_SYNTHESES_DIRECTORY = Path(__file__).resolve().parent


class LaboratorySynthesesSettings(BaseSettings):
    MINIO_ENDPOINT: str
    MINIO_BUCKET: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str

    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str

    model_config = SettingsConfigDict(
        env_file=LABORATORY_SYNTHESES_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}"
            f"/{self.DATABASE_NAME}"
        )


laboratory_syntheses_settings = LaboratorySynthesesSettings()
