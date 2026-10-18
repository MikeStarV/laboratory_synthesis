"""Файлы изображения и видео в MinIO; в PostgreSQL записываются их ключи."""

import json
import logging
from functools import lru_cache
from threading import Lock
from urllib.parse import quote
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

from .laboratory_syntheses_config import laboratory_syntheses_settings


logger = logging.getLogger(__name__)

LABORATORY_SYNTHESIS_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
LABORATORY_SYNTHESIS_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


def laboratory_synthesis_object_url(object_key: str) -> str:
    endpoint = (
        laboratory_syntheses_settings.MINIO_PUBLIC_ENDPOINT
        or laboratory_syntheses_settings.MINIO_ENDPOINT
    )
    return (
        f"{endpoint.rstrip('/')}/{laboratory_syntheses_settings.MINIO_BUCKET}/"
        f"{quote(object_key, safe='/')}"
    )


async def read_laboratory_synthesis_upload(
    upload: UploadFile, *, video: bool = False,
) -> tuple[str, bytes, str]:
    allowed_types = (
        LABORATORY_SYNTHESIS_VIDEO_TYPES if video
        else LABORATORY_SYNTHESIS_IMAGE_TYPES
    )
    content_type = (upload.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(
            415, "Для фото разрешены JPEG, PNG, WebP; для видео — MP4, WebM",
        )
    limit = (
        laboratory_syntheses_settings.LABORATORY_SYNTHESIS_VIDEO_MAX_BYTES
        if video
        else laboratory_syntheses_settings.LABORATORY_SYNTHESIS_IMAGE_MAX_BYTES
    )
    if upload.size is not None and upload.size > limit:
        raise HTTPException(413, "Файл превышает допустимый размер")
    payload = await upload.read(limit + 1)
    if len(payload) > limit:
        raise HTTPException(413, "Файл превышает допустимый размер")
    if not payload:
        raise HTTPException(422, "Нельзя загрузить пустой файл")

    signatures = {
        "image/jpeg": payload.startswith(b"\xff\xd8\xff"),
        "image/png": payload.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": payload[:4] == b"RIFF" and payload[8:12] == b"WEBP",
        "video/mp4": payload[4:8] == b"ftyp",
        "video/webm": payload.startswith(b"\x1a\x45\xdf\xa3"),
    }
    if not signatures[content_type]:
        raise HTTPException(415, "Содержимое файла не соответствует его типу")

    key = f"laboratory_syntheses/{uuid4().hex}{allowed_types[content_type]}"
    return key, payload, content_type


class LaboratorySynthesisMediaStorage:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=laboratory_syntheses_settings.MINIO_ENDPOINT,
            aws_access_key_id=laboratory_syntheses_settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=laboratory_syntheses_settings.MINIO_SECRET_KEY,
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=5,
                read_timeout=15,
                retries={"max_attempts": 1},
            ),
        )
        self.bucket = laboratory_syntheses_settings.MINIO_BUCKET
        self._ready = False
        self._lock = Lock()

    def ensure_bucket(self) -> None:
        with self._lock:
            if self._ready:
                return
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except ClientError as error:
                code = str(error.response.get("Error", {}).get("Code", ""))
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                except ClientError as creation_error:
                    if creation_error.response.get("Error", {}).get("Code") != (
                        "BucketAlreadyOwnedByYou"
                    ):
                        raise
            self.client.put_bucket_policy(
                Bucket=self.bucket,
                Policy=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket}/*"],
                    }],
                }),
            )
            self._ready = True

    def put(self, key: str, payload: bytes, content_type: str) -> None:
        self.ensure_bucket()
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=payload,
            ContentType=content_type, ContentDisposition="inline",
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def delete_safely(self, key: str) -> None:
        try:
            self.delete(key)
        except Exception:
            logger.warning("Не удалось очистить объект MinIO %s", key, exc_info=True)


@lru_cache(maxsize=1)
def get_laboratory_synthesis_media_storage() -> LaboratorySynthesisMediaStorage:
    return LaboratorySynthesisMediaStorage()
