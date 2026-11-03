"""HTTP-сценарии: настоящие ORM/маршруты, SQLite и fakeredis вместо сервисов."""
import asyncio
from contextlib import asynccontextmanager

import fakeredis.aioredis
import httpx
from redis.exceptions import ConnectionError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from laboratory_syntheses.laboratory_syntheses_app import app
from laboratory_syntheses.laboratory_syntheses_current_user import get_laboratory_synthesis_redis
from laboratory_syntheses.laboratory_syntheses_database import (
    LaboratorySynthesesDatabaseModel, get_laboratory_syntheses_database_session,
)
from laboratory_syntheses.laboratory_syntheses_database_models import LaboratorySynthesisUser
from laboratory_syntheses.laboratory_syntheses_storage import get_laboratory_synthesis_media_storage
from laboratory_syntheses.laboratory_syntheses_api import verify_laboratory_synthesis_password

API = "/api/laboratory_syntheses"
USERS = "/api/laboratory_synthesis_users"
PUBLICATION = {"laboratory_synthesis_description": "Описание синтеза",
               "laboratory_synthesis_duration_minutes": 20,
               "laboratory_synthesis_temperature_celsius": 25}


class MemoryStorage:
    def put(self, *args):
        pass

    def delete_safely(self, key):
        pass


@asynccontextmanager
async def environment():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(LaboratorySynthesesDatabaseModel.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def database():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_laboratory_syntheses_database_session] = database
    app.dependency_overrides[get_laboratory_synthesis_redis] = lambda: redis
    app.dependency_overrides[get_laboratory_synthesis_media_storage] = MemoryStorage
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://testserver") as client:
            yield client, redis, sessions
    finally:
        app.dependency_overrides.clear()
        await redis.aclose()
        await engine.dispose()


def credentials(name):
    return {"laboratory_synthesis_user_name": name,
            "laboratory_synthesis_user_password": "Test-password-123"}


async def register_login(client, name):
    result = await client.post(USERS, json=credentials(name))
    assert result.status_code == 201, result.text
    result = await client.post(USERS + "/login", json=credentials(name))
    assert result.status_code == 200, result.text
    assert "password" not in result.text
    return result.json()["laboratory_synthesis_user_id"]


async def create(client):
    return await client.post(API, data={"laboratory_synthesis_name": "Тестовый синтез"},
        files={"laboratory_synthesis_image": ("image.png", b"\x89PNG\r\n\x1a\nimage", "image/png"),
               "laboratory_synthesis_video": ("video.mp4", b"\x00\x00\x00\x18ftypisomvideo", "video/mp4")})


def test_two_users_business_process_and_guest_permissions():
    async def scenario():
        async with environment() as (client, redis, sessions):
            assert (await client.get(API)).json() == []
            for method, path, body in [
                ("get", API + "/draft", None),
                ("put", API + "/draft/publication", PUBLICATION),
                ("delete", API + "/1", None),
                ("post", API + "/1/likes", {"laboratory_synthesis_liked": 1}),
            ]:
                response = await client.request(method, path, **({"json": body} if body else {}))
                assert response.status_code == 401, response.text
            assert (await create(client)).status_code == 401
            author = await register_login(client, "author")
            result = await create(client)
            assert result.status_code == 201, result.text
            item_id = result.json()["laboratory_synthesis_id"]
            assert result.json()["laboratory_synthesis_creator"]["laboratory_synthesis_user_id"] == author
            assert (await create(client)).status_code == 409
            assert (await client.get(API + "/draft")).status_code == 200
            invalid = dict(PUBLICATION, laboratory_synthesis_creator_id=999)
            assert (await client.put(API + "/draft/publication", json=invalid)).status_code == 422
            result = await client.put(API + "/draft/publication", json=PUBLICATION)
            assert result.status_code == 200, result.text
            assert result.json()["laboratory_synthesis_status"] == "published"
            assert (await client.put(API + "/draft/publication", json=PUBLICATION)).status_code == 409
            assert (await client.get(API)).json()[0]["laboratory_synthesis_is_creator"] == 1
            assert (await client.get(API + "?laboratory_synthesis_max_duration=10")).json() == []
            await client.post(USERS + "/logout")
            guest = (await client.get(API)).json()[0]
            assert guest["laboratory_synthesis_is_creator"] == guest["laboratory_synthesis_liked"] == 0
            await register_login(client, "second")
            assert (await client.delete(f"{API}/{item_id}")).status_code == 403
            assert (await client.get(API + "/draft")).status_code == 404
            assert (await client.put(API + "/draft/publication", json=PUBLICATION)).status_code == 409
            for liked in (1, 1, 0):
                result = await client.post(f"{API}/{item_id}/likes", json={"laboratory_synthesis_liked": liked})
                assert result.status_code == 200, result.text
                assert result.json()["laboratory_synthesis_likes_count"] == liked
            assert (await client.get(f"{API}/feed/{item_id}?next=true")).status_code == 200
            await client.post(USERS + "/login", json=credentials("author"))
            assert (await client.delete(f"{API}/{item_id}")).status_code == 204
            assert (await client.get(API)).json() == []
            assert (await client.get(f"{API}/feed/{item_id}")).status_code == 404
    asyncio.run(scenario())


def test_sessions_logout_rotation_expiry_and_password_hash():
    async def scenario():
        async with environment() as (client, redis, sessions):
            user_id = await register_login(client, "author")
            old = client.cookies.get("session_id")
            assert await redis.get(f"session:{old}") == str(user_id)
            assert 0 < await redis.ttl(f"session:{old}") <= 900
            async with sessions() as db:
                user = await db.get(LaboratorySynthesisUser, user_id)
                assert user.laboratory_synthesis_user_password_hash.startswith("pbkdf2_sha256$")
                assert verify_laboratory_synthesis_password("Test-password-123", user.laboratory_synthesis_user_password_hash)
            assert (await client.post(USERS, json=credentials("author"))).status_code == 409
            wrong = dict(credentials("author"), laboratory_synthesis_user_password="wrong-password")
            assert (await client.post(USERS + "/login", json=wrong)).status_code == 401
            result = await client.post(USERS + "/login", json=credentials("author"))
            cookie = result.headers["set-cookie"].lower()
            assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
            current = client.cookies.get("session_id")
            assert old != current and await redis.get(f"session:{old}") is None
            assert (await client.post(USERS + "/logout")).status_code == 204
            assert await redis.get(f"session:{current}") is None
            assert client.cookies.get("session_id") is None
            client.cookies.set("session_id", current)
            assert (await client.get(API + "/draft")).status_code == 401
            await redis.setex(f"session:{current}", 900, user_id)
            await redis.expireat(f"session:{current}", 1)
            assert await redis.get(f"session:{current}") is None
            assert (await client.get(API + "/draft")).status_code == 401
            assert (await client.get(API)).status_code == 200
            await redis.set(f"session:{current}", "broken")
            assert (await client.get(API + "/draft")).status_code == 401
            await redis.set(f"session:{current}", 99999)
            assert (await client.get(API + "/draft")).status_code == 401
    asyncio.run(scenario())


def test_redis_failure_fails_closed_and_guest_needs_no_redis():
    async def scenario():
        async with environment() as (client, redis, sessions):
            await register_login(client, "author")
            class BrokenRedis:
                async def get(self, key):
                    raise ConnectionError("unavailable")
                async def delete(self, key):
                    raise ConnectionError("unavailable")
            app.dependency_overrides[get_laboratory_synthesis_redis] = BrokenRedis
            assert (await client.get(API + "/draft")).status_code == 503
            assert (await client.post(USERS + "/logout")).status_code == 503
            client.cookies.clear()
            assert (await client.get(API)).status_code == 200
            assert (await client.get(API + "/draft")).status_code == 401
    asyncio.run(scenario())


def test_swagger_security_and_legacy_write_routes():
    spec = app.openapi()
    assert spec["components"]["securitySchemes"]["APIKeyCookie"]["name"] == "session_id"
    assert not spec["paths"][API]["get"].get("security")
    assert spec["paths"][API + "/draft/publication"]["put"]["security"]
    assert all("post" not in methods for path, methods in spec["paths"].items()
               if path.startswith("/laboratory_syntheses"))
