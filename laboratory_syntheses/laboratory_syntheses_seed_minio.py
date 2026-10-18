"""MinIO: публичное чтение учебных медиа, без изменения пользовательских файлов."""
import json
import mimetypes
import os
import sys

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from .laboratory_syntheses_media import LABORATORY_SYNTHESES_DIRECTORY, laboratory_synthesis_media_url

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000").rstrip("/")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "synthesis-media")


def get_s3_client():
    return boto3.client(
        "s3", endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=3, read_timeout=10, retries={"max_attempts": 1}),
    )


def ensure_bucket(s3):
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as error:
        if str(error.response.get("Error", {}).get("Code")) not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        s3.create_bucket(Bucket=MINIO_BUCKET)
    s3.put_bucket_policy(Bucket=MINIO_BUCKET, Policy=json.dumps({
        "Version": "2012-10-17", "Statement": [{
            "Effect": "Allow", "Principal": "*", "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"],
        }],
    }))
    # Для img/video публичного GET достаточно. Запись идёт через сервер,
    # поэтому отдельный S3 put_bucket_cors для браузера не требуется.


def upload_demo_media(s3):
    media = LABORATORY_SYNTHESES_DIRECTORY / "static/media"
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".mp4", ".webm"}
    for path in sorted(media.iterdir()):
        if path.suffix.lower() not in allowed:
            continue
        s3.put_object(Bucket=MINIO_BUCKET, Key=path.name, Body=path.read_bytes(),
                      ContentType=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                      ContentDisposition="inline")
        print("Медиа:", laboratory_synthesis_media_url(path.name))


def prepare_demo_media():
    s3 = get_s3_client()
    ensure_bucket(s3)
    upload_demo_media(s3)


def main():
    try:
        prepare_demo_media()
    except (BotoCoreError, ClientError, OSError) as error:
        print(f"MinIO недоступен по {MINIO_ENDPOINT}: {error}. Запустите Docker Desktop с WSL Integration, "
              "затем docker compose -f laboratory_syntheses/docker-compose.yml up -d --wait.", file=sys.stderr)
        raise SystemExit(1)
    print(f"Бакет {MINIO_BUCKET} готов; медиа доступны для анонимного чтения.")


if __name__ == "__main__":
    main()
