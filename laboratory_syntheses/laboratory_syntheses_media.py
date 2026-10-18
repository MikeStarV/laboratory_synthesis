"""MinIO для карточек; локальные SSR-медиа для пустых и недоступных URL."""

import json
import mimetypes
import os
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from starlette.concurrency import run_in_threadpool

LABORATORY_SYNTHESES_DIRECTORY = Path(__file__).resolve().parent
load_dotenv(LABORATORY_SYNTHESES_DIRECTORY / ".env")
LABORATORY_SYNTHESES_DEFAULT_IMAGE_URL = "/laboratory_syntheses/static/media/laboratory_syntheses_default.svg"
LABORATORY_SYNTHESES_DEFAULT_VIDEO_URL = "/laboratory_syntheses/static/media/laboratory_syntheses_default.mp4"

_media_cache = {}
_media_cache_lock = Lock()
_minio_unavailable_until = 0.0


def laboratory_synthesis_media_base_url():
    explicit = os.getenv("LABORATORY_SYNTHESES_MEDIA_BASE_URL", "").rstrip("/")
    endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT") or os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    return explicit or endpoint.rstrip("/") + "/" + os.getenv("MINIO_BUCKET", "synthesis-media")


def laboratory_synthesis_media_url(laboratory_synthesis_media_key: str) -> str:
    return laboratory_synthesis_media_base_url() + "/" + quote(laboratory_synthesis_media_key, safe="/")


def laboratory_synthesis_media_key(url):
    if not url:
        return None
    for base in {
        laboratory_synthesis_media_base_url(),
        os.getenv("MINIO_ENDPOINT", "http://localhost:9000").rstrip("/") + "/" + os.getenv("MINIO_BUCKET", "synthesis-media"),
    }:
        if url.startswith(base + "/"):
            key = unquote(url[len(base) + 1:])
            if key and not key.startswith("/") and ".." not in key.split("/"):
                return key
    return None


def laboratory_synthesis_media_available(key, kind):
    """Проверяется именно анонимный HEAD: закрытый бакет не считается доступным."""
    global _minio_unavailable_until
    now = monotonic()
    cache_key = (key, kind)
    with _media_cache_lock:
        cached = _media_cache.get(cache_key)
        if cached and now - cached[0] < 3:
            return cached[1]
        if now < _minio_unavailable_until:
            return False
    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000").rstrip("/")
    bucket = os.getenv("MINIO_BUCKET", "synthesis-media")
    probe_url = endpoint + "/" + bucket + "/" + quote(key, safe="/")
    try:
        with urlopen(Request(probe_url, method="HEAD"), timeout=0.8) as result:
            available = result.status == 200 and result.headers.get("Content-Type", "").startswith(kind + "/")
    except HTTPError:
        available = False
    except (OSError, URLError):
        available = False
        with _media_cache_lock:
            _minio_unavailable_until = monotonic() + 2
    with _media_cache_lock:
        _media_cache[cache_key] = (monotonic(), available)
    return available


def get_laboratory_synthesis_display_media(synthesis):
    urls = {}
    keys = {}
    for kind, default in [
        ("image", LABORATORY_SYNTHESES_DEFAULT_IMAGE_URL),
        ("video", LABORATORY_SYNTHESES_DEFAULT_VIDEO_URL),
    ]:
        stored_key = getattr(synthesis, "laboratory_synthesis_" + kind + "_key", None)
        stored_url = getattr(synthesis, "laboratory_synthesis_" + kind + "_url", None)
        key = stored_key or laboratory_synthesis_media_key(stored_url)
        keys[kind] = key
        urls[kind + "_url"] = (
            laboratory_synthesis_media_url(key)
            if key and laboratory_synthesis_media_available(key, kind)
            else default
        )
    urls["video_type"] = mimetypes.guess_type(urls["video_url"])[0] or "video/mp4"
    manifest_file = LABORATORY_SYNTHESES_DIRECTORY / "static/media/laboratory_syntheses_media_sources.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    basename = Path(keys["image"] or "").stem
    credit = manifest.get(basename)
    if not credit or urls["image_url"] == LABORATORY_SYNTHESES_DEFAULT_IMAGE_URL:
        credit = None
    urls["credit"] = credit
    return urls


async def resolve_laboratory_syntheses_media(syntheses):
    def resolve():
        return {
            synthesis.laboratory_synthesis_id: get_laboratory_synthesis_display_media(synthesis)
            for synthesis in syntheses
        }
    return await run_in_threadpool(resolve)

async def resolve_laboratory_synthesis_media(synthesis):
    return await run_in_threadpool(get_laboratory_synthesis_display_media, synthesis)
