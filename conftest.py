"""Изолированные настройки тестов; рабочий .env не требуется."""
import os

for key, value in {
    "DATABASE_HOST": "localhost", "DATABASE_PORT": "5433",
    "DATABASE_USER": "test", "DATABASE_PASSWORD": "test", "DATABASE_NAME": "test",
    "MINIO_ENDPOINT": "http://localhost:9000", "MINIO_BUCKET": "test",
    "MINIO_ACCESS_KEY": "test", "MINIO_SECRET_KEY": "test",
}.items():
    os.environ.setdefault(key, value)
