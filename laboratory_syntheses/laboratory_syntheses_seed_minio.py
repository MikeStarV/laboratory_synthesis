"""Подключение к MinIO и загрузка демонстрационных медиафайлов."""

import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .laboratory_syntheses_media import LABORATORY_SYNTHESES_DIRECTORY


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000").rstrip("/")
MINIO_PUBLIC_ENDPOINT = os.getenv(
    "MINIO_PUBLIC_ENDPOINT",
    MINIO_ENDPOINT,
).rstrip("/")

MINIO_ACCESS_KEY = os.getenv(
    "MINIO_ACCESS_KEY",
    os.getenv("MINIO_ROOT_USER", "minioadmin"),
)

MINIO_SECRET_KEY = os.getenv(
    "MINIO_SECRET_KEY",
    os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123"),
)

MINIO_BUCKET = os.getenv("MINIO_BUCKET", "synthesis-media")


def get_s3_client():
    """Создать клиент для работы с MinIO."""

    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def media_url(object_name: str) -> str:
    """Получить публичный URL объекта из MinIO."""

    encoded_name = quote(object_name.lstrip("/"))
    return f"{MINIO_PUBLIC_ENDPOINT}/{MINIO_BUCKET}/{encoded_name}"


def ensure_bucket(s3) -> None:
    """Создать бакет и разрешить публичное чтение файлов."""

    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as error:
        code = str(error.response.get("Error", {}).get("Code", ""))

        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

        s3.create_bucket(Bucket=MINIO_BUCKET)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"],
            }
        ],
    }

    s3.put_bucket_policy(
        Bucket=MINIO_BUCKET,
        Policy=json.dumps(policy),
    )

    s3.put_bucket_cors(
        Bucket=MINIO_BUCKET,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["GET", "HEAD"],
                    "AllowedHeaders": ["*"],
                    "ExposeHeaders": [
                        "Accept-Ranges",
                        "Content-Length",
                        "Content-Range",
                    ],
                    "MaxAgeSeconds": 3600,
                }
            ]
        },
    )


def upload_demo_media(s3) -> None:
    """Загрузить изображения и видео из static/media."""

    media_directory: Path = (
        LABORATORY_SYNTHESES_DIRECTORY / "static" / "media"
    )

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".svg",
        ".mp4",
        ".webm",
    }

    if not media_directory.exists():
        raise FileNotFoundError(
            f"Папка с медиа не найдена: {media_directory}"
        )

    for media_file in sorted(media_directory.rglob("*")):
        if not media_file.is_file():
            continue

        if media_file.suffix.lower() not in allowed_extensions:
            continue

        object_name = media_file.relative_to(media_directory).as_posix()
        content_type = (
            mimetypes.guess_type(media_file.name)[0]
            or "application/octet-stream"
        )

        s3.upload_file(
            str(media_file),
            MINIO_BUCKET,
            object_name,
            ExtraArgs={
                "ContentType": content_type,
                "ContentDisposition": "inline",
            },
        )

        print(f"Загружен: {media_url(object_name)}")


def main() -> None:
    s3 = get_s3_client()
    ensure_bucket(s3)
    upload_demo_media(s3)
    print(f"Бакет {MINIO_BUCKET!r} готов")


if __name__ == "__main__":
    main()
