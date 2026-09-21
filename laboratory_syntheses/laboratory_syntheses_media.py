"""Публичные адреса MinIO; локальные материалы для автономного просмотра."""
import os
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv

LABORATORY_SYNTHESES_DIRECTORY = Path(__file__).resolve().parent
load_dotenv(LABORATORY_SYNTHESES_DIRECTORY / ".env")


def laboratory_synthesis_media_url(laboratory_synthesis_media_key: str) -> str:
    laboratory_syntheses_media_base = os.getenv("LABORATORY_SYNTHESES_MEDIA_BASE_URL", "").rstrip("/")
    if not laboratory_syntheses_media_base:
        laboratory_syntheses_media_base = "/laboratory_syntheses/static/media"
    return f"{laboratory_syntheses_media_base}/{quote(laboratory_synthesis_media_key, safe='')}"
