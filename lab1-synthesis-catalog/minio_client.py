import os
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "synthesis-media")


def build_media_url(object_key: str) -> str:
    """Формирует публичный URL объекта в MinIO для использования в img/video."""
    return f"{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_key}"
