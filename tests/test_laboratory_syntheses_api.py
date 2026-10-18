"""Проверка HTTP-сценариев ЛР3 без пользовательских PostgreSQL и MinIO."""

import os
import unittest
from unittest.mock import patch

for key, value in {
    "DATABASE_HOST": "localhost", "DATABASE_PORT": "5433",
    "DATABASE_USER": "synthesis_user", "DATABASE_PASSWORD": "synthesis_password",
    "DATABASE_NAME": "synthesis_db", "MINIO_ENDPOINT": "http://localhost:9000",
    "MINIO_BUCKET": "synthesis-media", "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "minioadmin123",
}.items():
    os.environ.setdefault(key, value)

import httpx
from botocore.stub import ANY, Stubber
from sqlalchemy import event, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from laboratory_syntheses.laboratory_syntheses_app import app
from laboratory_syntheses.laboratory_syntheses_config import laboratory_syntheses_settings
from laboratory_syntheses.laboratory_syntheses_current_user import (
    get_laboratory_synthesis_current_user,
)
from laboratory_syntheses.laboratory_syntheses_database import (
    LaboratorySynthesesDatabaseModel, get_laboratory_syntheses_database_session,
)
from laboratory_syntheses.laboratory_syntheses_database_models import (
    LaboratorySynthesis, LaboratorySynthesisLike, LaboratorySynthesisStatus,
    LaboratorySynthesisUser,
)
from laboratory_syntheses.laboratory_syntheses_storage import (
    LaboratorySynthesisMediaStorage, get_laboratory_synthesis_media_storage,
)


API = "/api/laboratory_syntheses"
USERS = "/api/laboratory_synthesis_users"
PNG = b"\x89PNG\r\n\x1a\n" + b"laboratory-image"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"laboratory-video"


class MemorySynthesisStorage:
    def __init__(self):
        self.objects = {}
        self.fail_video = False

    def put(self, key, payload, content_type):
        if self.fail_video and content_type.startswith("video/"):
            raise OSError("Storage failure")
        self.objects[key] = (payload, content_type)

    def delete_safely(self, key):
        self.objects.pop(key, None)


class LaboratorySynthesesApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = os.environ.get(
            "LABORATORY_SYNTHESIS_TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:",
        )
        parsed = make_url(url)
        if parsed.get_backend_name() != "sqlite" and not (
            parsed.database or ""
        ).endswith("_test"):
            raise ValueError("Интеграционные тесты разрешены только для БД с суффиксом _test")
        self.engine = create_async_engine(url)
        if parsed.get_backend_name() == "sqlite":
            @event.listens_for(self.engine.sync_engine, "connect")
            def sqlite_foreign_keys(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
        async with self.engine.begin() as connection:
            await connection.run_sync(LaboratorySynthesesDatabaseModel.metadata.drop_all)
            await connection.run_sync(LaboratorySynthesesDatabaseModel.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([
                LaboratorySynthesisUser(laboratory_synthesis_user_name="Михаил"),
                LaboratorySynthesisUser(laboratory_synthesis_user_name="Лаборатория"),
            ])
            await session.flush()
            for synthesis_id, owner, status, duration in [
                (1, 1, LaboratorySynthesisStatus.PUBLISHED, 20),
                (3, 1, LaboratorySynthesisStatus.DELETED, 10),
                (7, 2, LaboratorySynthesisStatus.PUBLISHED, 60),
                (9, 2, LaboratorySynthesisStatus.DRAFT, 30),
            ]:
                session.add(LaboratorySynthesis(
                    laboratory_synthesis_id=synthesis_id,
                    laboratory_synthesis_creator_id=owner,
                    laboratory_synthesis_status=status,
                    laboratory_synthesis_name=f"Лабораторный синтез {synthesis_id}",
                    laboratory_synthesis_description="Описание синтеза",
                    laboratory_synthesis_duration_minutes=duration,
                    laboratory_synthesis_temperature_celsius=20,
                    laboratory_synthesis_image_url="http://localhost:9000/synthesis-media/demo.jpg",
                    laboratory_synthesis_video_url="http://localhost:9000/synthesis-media/demo.mp4",
                ))
            await session.flush()
            if parsed.get_backend_name() == "postgresql":
                await session.execute(select(func.setval(
                    func.pg_get_serial_sequence(
                        "laboratory_syntheses", "laboratory_synthesis_id",
                    ), 9, True,
                )))
            session.add(LaboratorySynthesisLike(
                laboratory_synthesis_id=1, laboratory_synthesis_user_id=2,
            ))
            await session.commit()

        async def database():
            async with self.sessions() as session:
                yield session

        self.storage = MemorySynthesisStorage()
        app.dependency_overrides[get_laboratory_syntheses_database_session] = database
        app.dependency_overrides[get_laboratory_synthesis_media_storage] = lambda: self.storage
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://laboratory.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        async with self.engine.begin() as connection:
            await connection.run_sync(LaboratorySynthesesDatabaseModel.metadata.drop_all)
        await self.engine.dispose()

    async def upload(self, fields=None, image=PNG, video=MP4):
        data = {
            "laboratory_synthesis_name": "Получение йодоформа",
            "laboratory_synthesis_description": "Демонстрационная запись для проверки API",
            "laboratory_synthesis_duration_minutes": "45",
            "laboratory_synthesis_temperature_celsius": "50",
        }
        data.update(fields or {})
        return await self.client.post(API, data=data, files={
            "laboratory_synthesis_image": ("фотография.png", image, "image/png"),
            "laboratory_synthesis_video": ("видео.mp4", video, "video/mp4"),
        })

    async def test_catalog_filters_and_author_flags(self):
        response = await self.client.get(API)
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual([row["laboratory_synthesis_id"] for row in rows], [1, 7])
        self.assertEqual([row["laboratory_synthesis_is_creator"] for row in rows], [1, 0])
        self.assertEqual(rows[0]["laboratory_synthesis_likes_count"], 1)
        self.assertEqual(rows[0]["laboratory_synthesis_liked"], 0)
        self.assertEqual(rows[0]["laboratory_synthesis_creator"]["laboratory_synthesis_user_id"], 1)
        filtered = await self.client.get(API, params={"laboratory_synthesis_max_duration": 30})
        self.assertEqual([row["laboratory_synthesis_id"] for row in filtered.json()], [1])
        empty = await self.client.get(API, params={"laboratory_synthesis_max_duration": 1})
        self.assertEqual(empty.json(), [])
        self.assertNotIn("password", response.text)

    async def test_feed_skips_gaps_and_wraps(self):
        for path, expected in [
            ("/feed", 1), ("/feed/1", 1), ("/feed/1?next=true", 7),
            ("/feed/7?next=true", 1), ("/feed/3?next=true", 7),
        ]:
            response = await self.client.get(API + path)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["laboratory_synthesis_id"], expected)
        for path in ["/feed/3", "/feed/9", "/feed/999"]:
            self.assertEqual((await self.client.get(API + path)).status_code, 404)
        self.assertEqual((await self.client.get(API + "/feed/-1")).status_code, 422)

    async def test_save_reuses_single_draft_and_replaces_media(self):
        self.assertEqual((await self.client.get(API + "/draft")).status_code, 404)
        first = await self.upload()
        self.assertEqual(first.status_code, 201, first.text)
        synthesis_id = first.json()["laboratory_synthesis_id"]
        first_keys = set(self.storage.objects)
        self.assertEqual(len(first_keys), 2)
        for key in first_keys:
            self.assertRegex(key, r"^laboratory_syntheses/[a-f0-9]{32}\.(png|mp4)$")
        response = await self.upload({"laboratory_synthesis_name": "Обновлённый синтез"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["laboratory_synthesis_id"], synthesis_id)
        self.assertFalse(first_keys & set(self.storage.objects))
        self.assertEqual(len(self.storage.objects), 2)
        draft = (await self.client.get(API + "/draft")).json()
        self.assertEqual(draft["laboratory_synthesis_name"], "Обновлённый синтез")
        self.assertEqual(draft["laboratory_synthesis_creator"]["laboratory_synthesis_user_id"], 1)
        self.assertNotIn(synthesis_id, [
            row["laboratory_synthesis_id"] for row in (await self.client.get(API)).json()
        ])

    async def test_edit_draft_keeps_media_when_no_files_selected(self):
        original = (await self.upload()).json()
        response = await self.client.post(API, data={
            "laboratory_synthesis_name": "Новое название",
            "laboratory_synthesis_description": "Новое описание",
            "laboratory_synthesis_duration_minutes": "90",
            "laboratory_synthesis_temperature_celsius": "0",
        })
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        self.assertEqual(updated["laboratory_synthesis_id"], original["laboratory_synthesis_id"])
        self.assertEqual(updated["laboratory_synthesis_image_key"], original["laboratory_synthesis_image_key"])
        self.assertEqual(updated["laboratory_synthesis_video_key"], original["laboratory_synthesis_video_key"])
        self.assertEqual(len(self.storage.objects), 2)

    async def test_new_draft_requires_both_files(self):
        response = await self.client.post(API, data={
            "laboratory_synthesis_name": "Название",
            "laboratory_synthesis_description": "Описание",
            "laboratory_synthesis_duration_minutes": "20",
            "laboratory_synthesis_temperature_celsius": "20",
        })
        self.assertEqual(response.status_code, 422)
        self.assertFalse(self.storage.objects)

    async def test_publish_and_create_next_draft(self):
        synthesis_id = (await self.upload()).json()["laboratory_synthesis_id"]
        path = f"{API}/{synthesis_id}/publication"
        forbidden = await self.client.put(path, json={"laboratory_synthesis_status": "draft"})
        self.assertEqual(forbidden.status_code, 422)
        published = await self.client.put(path, json={})
        self.assertEqual(published.status_code, 200, published.text)
        self.assertEqual(published.json()["laboratory_synthesis_status"], "published")
        self.assertIsNotNone(published.json()["laboratory_synthesis_formed_at"])
        self.assertEqual((await self.client.put(path)).status_code, 409)
        self.assertEqual((await self.client.get(API + "/draft")).status_code, 404)
        next_draft = await self.upload()
        self.assertEqual(next_draft.status_code, 201, next_draft.text)
        self.assertNotEqual(next_draft.json()["laboratory_synthesis_id"], synthesis_id)
        self.assertEqual((await self.client.put(f"{API}/9/publication")).status_code, 403)

    async def test_likes_are_idempotent_and_can_be_removed(self):
        for desired, expected_count in [(1, 1), (1, 1), (0, 0), (0, 0)]:
            response = await self.client.post(
                f"{API}/7/likes", json={"laboratory_synthesis_liked": desired},
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["laboratory_synthesis_liked"], desired)
            self.assertEqual(response.json()["laboratory_synthesis_likes_count"], expected_count)
        for value in [2, -1, "1", True]:
            self.assertEqual((await self.client.post(
                f"{API}/7/likes", json={"laboratory_synthesis_liked": value},
            )).status_code, 422)
        self.assertEqual((await self.client.post(
            f"{API}/9/likes", json={"laboratory_synthesis_liked": 1},
        )).status_code, 404)

    async def test_delete_is_soft_and_owner_only(self):
        self.assertEqual((await self.client.delete(f"{API}/7")).status_code, 403)
        self.assertEqual((await self.client.delete(f"{API}/1")).status_code, 204)
        self.assertEqual((await self.client.delete(f"{API}/1")).status_code, 404)
        self.assertEqual((await self.client.get(f"{API}/feed/1")).status_code, 404)
        self.assertEqual((await self.client.post(
            f"{API}/1/likes", json={"laboratory_synthesis_liked": 1},
        )).status_code, 404)
        async with self.sessions() as session:
            row = await session.get(LaboratorySynthesis, 1)
            self.assertEqual(row.laboratory_synthesis_status, LaboratorySynthesisStatus.DELETED)
            self.assertEqual(await session.scalar(
                select(func.count()).select_from(LaboratorySynthesisLike),
            ), 1)
        self.assertEqual((await self.client.post("/laboratory_syntheses/7/delete")).status_code, 403)

    async def test_forbidden_fields_and_invalid_inputs(self):
        for field in [
            "laboratory_synthesis_id", "laboratory_synthesis_status",
            "laboratory_synthesis_creator_id", "laboratory_synthesis_created_at",
            "laboratory_synthesis_formed_at", "laboratory_synthesis_moderator_id",
        ]:
            self.assertEqual((await self.upload({field: "1"})).status_code, 422)
        for fields in [
            {"laboratory_synthesis_name": "   "},
            {"laboratory_synthesis_duration_minutes": "91"},
            {"laboratory_synthesis_duration_minutes": "0"},
            {"laboratory_synthesis_temperature_celsius": "-274"},
            {"laboratory_synthesis_temperature_celsius": "nan"},
        ]:
            self.assertEqual((await self.upload(fields)).status_code, 422)
        self.assertEqual(self.storage.objects, {})

    async def test_upload_rejects_empty_fake_and_oversized_files(self):
        self.assertEqual((await self.upload(image=b"")).status_code, 422)
        self.assertEqual((await self.upload(image=b"not an image")).status_code, 415)
        self.assertEqual((await self.upload(video=b"not a video")).status_code, 415)
        with patch.object(laboratory_syntheses_settings, "LABORATORY_SYNTHESIS_IMAGE_MAX_BYTES", 4):
            self.assertEqual((await self.upload()).status_code, 413)
        self.assertEqual(self.storage.objects, {})

    async def test_minio_failure_does_not_leave_a_draft_or_objects(self):
        self.storage.fail_video = True
        response = await self.upload()
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(self.storage.objects, {})
        self.assertEqual((await self.client.get(API + "/draft")).status_code, 404)

    async def test_failed_replacement_keeps_original_draft(self):
        first = (await self.upload()).json()
        old_objects = self.storage.objects.copy()
        self.storage.fail_video = True
        self.assertEqual((await self.upload(
            {"laboratory_synthesis_name": "Не должно сохраниться"},
        )).status_code, 503)
        self.assertEqual(self.storage.objects, old_objects)
        current = (await self.client.get(API + "/draft")).json()
        self.assertEqual(current["laboratory_synthesis_name"], first["laboratory_synthesis_name"])

    async def test_database_failure_cleans_uploaded_objects(self):
        async def broken_database():
            async with self.sessions() as session:
                with patch.object(session, "commit", side_effect=SQLAlchemyError("failure")):
                    yield session
        app.dependency_overrides[get_laboratory_syntheses_database_session] = broken_database
        self.assertEqual((await self.upload()).status_code, 503)
        self.assertEqual(self.storage.objects, {})

    async def test_registration_hides_hash_and_does_not_change_current_user(self):
        body = {
            "laboratory_synthesis_user_name": "new_lab_user",
            "laboratory_synthesis_user_password": "LaboratoryPass123!",
        }
        result = await self.client.post(USERS, json=body)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(set(result.json()), {
            "laboratory_synthesis_user_id", "laboratory_synthesis_user_name",
        })
        async with self.sessions() as session:
            user = await session.get(
                LaboratorySynthesisUser, result.json()["laboratory_synthesis_user_id"],
            )
            self.assertTrue(user.laboratory_synthesis_user_password_hash.startswith("pbkdf2_sha256$"))
            self.assertNotIn(body["laboratory_synthesis_user_password"], user.laboratory_synthesis_user_password_hash)
        self.assertEqual((await self.client.post(USERS, json=body)).status_code, 409)
        self.assertEqual((await self.client.post(
            USERS, json={**body, "laboratory_synthesis_user_id": 100},
        )).status_code, 422)
        self.assertEqual(get_laboratory_synthesis_current_user().laboratory_synthesis_user_id, 1)
        self.assertIs(
            get_laboratory_synthesis_current_user(), get_laboratory_synthesis_current_user(),
        )

    async def test_authentication_stubs_and_openapi(self):
        for path in ["/login", "/logout"]:
            self.assertEqual((await self.client.post(USERS + path)).status_code, 501)
        result = await self.client.get("/api/openapi.json")
        self.assertEqual(result.status_code, 200)
        self.assertIn(API, result.json()["paths"])
        self.assertIn("multipart/form-data", result.json()["paths"][API]["post"]["requestBody"]["content"])

    async def test_create_publish_like_and_delete(self):
        created = await self.upload()
        self.assertEqual(created.status_code, 201, created.text)
        synthesis_id = created.json()["laboratory_synthesis_id"]
        draft = await self.client.get(API + "/draft")
        self.assertEqual(draft.status_code, 200)
        self.assertEqual(draft.json()["laboratory_synthesis_id"], synthesis_id)
        published = await self.client.put(f"{API}/{synthesis_id}/publication")
        self.assertEqual(published.status_code, 200, published.text)
        liked = await self.client.post(
            f"{API}/{synthesis_id}/likes", json={"laboratory_synthesis_liked": 1},
        )
        self.assertEqual(liked.status_code, 200, liked.text)
        self.assertEqual(liked.json()["laboratory_synthesis_liked"], 1)
        deleted = await self.client.delete(f"{API}/{synthesis_id}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            (await self.client.get(f"{API}/feed/{synthesis_id}")).status_code, 404,
        )


class LaboratorySynthesisS3Tests(unittest.TestCase):
    def test_boto3_upload_and_cleanup_use_generated_key_and_bucket(self):
        storage = LaboratorySynthesisMediaStorage()
        key = "laboratory_syntheses/0123456789abcdef0123456789abcdef.png"
        with Stubber(storage.client) as stub:
            stub.add_response("head_bucket", {}, {"Bucket": storage.bucket})
            stub.add_response("put_bucket_policy", {}, {"Bucket": storage.bucket, "Policy": ANY})
            stub.add_response("put_object", {}, {
                "Bucket": storage.bucket, "Key": key, "Body": PNG,
                "ContentType": "image/png", "ContentDisposition": "inline",
            })
            stub.add_response("delete_object", {}, {"Bucket": storage.bucket, "Key": key})
            storage.put(key, PNG, "image/png")
            storage.delete(key)
            stub.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()
