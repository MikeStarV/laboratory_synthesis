from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


LABORATORY_SYNTHESES_DIRECTORY = Path(__file__).resolve().parent


class LaboratorySynthesesSettings(BaseSettings):
    MINIO_ENDPOINT: str
    MINIO_BUCKET: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_PUBLIC_ENDPOINT: str | None = None
    LABORATORY_SYNTHESIS_IMAGE_MAX_BYTES: int = 10 * 1024 * 1024
    LABORATORY_SYNTHESIS_VIDEO_MAX_BYTES: int = 64 * 1024 * 1024

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
            f"{quote(self.DATABASE_USER, safe='')}:{quote(self.DATABASE_PASSWORD, safe='')}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}"
            f"/{self.DATABASE_NAME}"
        )


laboratory_syntheses_settings = LaboratorySynthesesSettings()
