"""Пограничные сценарии SSR и учебных данных; SQLite не заменяет проверку PostgreSQL."""
import os
import unittest
from unittest.mock import patch

for key, value in {
    "DATABASE_HOST": "localhost", "DATABASE_PORT": "5433", "DATABASE_USER": "synthesis_user",
    "DATABASE_PASSWORD": "synthesis_password", "DATABASE_NAME": "synthesis_db",
    "MINIO_ENDPOINT": "http://localhost:9000", "MINIO_BUCKET": "synthesis-media",
    "MINIO_ACCESS_KEY": "minioadmin", "MINIO_SECRET_KEY": "minioadmin123",
}.items():
    os.environ.setdefault(key, value)

import httpx
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from laboratory_syntheses.laboratory_syntheses_app import app
from laboratory_syntheses.laboratory_syntheses_database import (
    LaboratorySynthesesDatabaseModel, get_laboratory_syntheses_database_session,
)
from laboratory_syntheses.laboratory_syntheses_database_models import (
    LaboratorySynthesis, LaboratorySynthesisStatus, LaboratorySynthesisUser,
)
from laboratory_syntheses.laboratory_syntheses_media import get_laboratory_synthesis_display_media
from laboratory_syntheses.laboratory_syntheses_seed_database import seed_database

API_ENABLED = any(route.path == "/api/laboratory_syntheses" for route in app.routes)


class LaboratorySynthesesSsrTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.statements = []
        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def record(connection, cursor, statement, parameters, context, many):
            self.statements.append(statement)
        async with self.engine.begin() as connection:
            await connection.run_sync(LaboratorySynthesesDatabaseModel.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([LaboratorySynthesisUser(laboratory_synthesis_user_id=i,
                laboratory_synthesis_user_name=f"author_{i}") for i in (1, 2)])
            await session.flush()
            for synthesis_id, owner, status, duration in ((2, 1, "published", 20),
                    (4, 1, "deleted", 30), (10, 2, "published", 90), (15, 1, "draft", 40)):
                session.add(LaboratorySynthesis(
                    laboratory_synthesis_id=synthesis_id, laboratory_synthesis_creator_id=owner,
                    laboratory_synthesis_name=f"Синтез {synthesis_id}",
                    laboratory_synthesis_description="Подробное описание лабораторного синтеза. " * 10,
                    laboratory_synthesis_status=LaboratorySynthesisStatus(status),
                    laboratory_synthesis_duration_minutes=duration,
                    laboratory_synthesis_temperature_celsius=0,
                    laboratory_synthesis_image_url="http://localhost:9000/synthesis-media/missing.jpg",
                    laboratory_synthesis_video_url=None,
                ))
            await session.commit()
        async def database():
            async with self.sessions() as session:
                yield session
        app.dependency_overrides[get_laboratory_syntheses_database_session] = database
        self.media_patch = patch("laboratory_syntheses.laboratory_syntheses_media.laboratory_synthesis_media_available", return_value=False)
        self.media_patch.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://laboratory.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.media_patch.stop()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_filter_endpoints_and_deleted_visibility(self):
        empty = await self.client.get("/laboratory_syntheses?laboratory_synthesis_max_duration=0")
        self.assertEqual(empty.status_code, 200)
        self.assertNotIn("Синтез 2", empty.text)
        self.assertIn('value="0"', empty.text)
        full = await self.client.get("/laboratory_syntheses?laboratory_synthesis_max_duration=90")
        self.assertIn("Синтез 2", full.text)
        self.assertIn("Синтез 10", full.text)
        self.assertNotIn("Синтез 4", full.text)
        self.assertNotIn("Синтез 15", full.text)
        self.assertEqual((await self.client.get("/laboratory_syntheses?laboratory_synthesis_max_duration=91")).status_code, 422)
        self.assertEqual((await self.client.get("/laboratory_syntheses/feed/4")).status_code, 404)
        if API_ENABLED:
            response = await self.client.get("/api/laboratory_syntheses?laboratory_synthesis_max_duration=0")
            self.assertEqual(response.json(), [])

    async def test_next_handles_gaps_and_wraps_with_limit_one(self):
        self.statements.clear()
        response = await self.client.get("/laboratory_syntheses/feed/2?next=true")
        self.assertIn("Синтез 10", response.text)
        queries = [query for query in self.statements if query.startswith("SELECT laboratory_syntheses.laboratory_synthesis_id")]
        self.assertTrue(queries)
        self.assertTrue(all("LIMIT" in query for query in queries))
        response = await self.client.get("/laboratory_syntheses/feed/10?next=true")
        self.assertIn("Синтез 2", response.text)

    async def test_soft_delete_sql_and_foreign_owner(self):
        self.assertEqual((await self.client.post("/laboratory_syntheses/10/delete")).status_code, 403)
        self.statements.clear()
        self.assertEqual((await self.client.post("/laboratory_syntheses/2/delete")).status_code, 303)
        updates = [query for query in self.statements if "UPDATE laboratory_syntheses" in query]
        self.assertTrue(updates)
        self.assertIn("laboratory_synthesis_status = 'deleted'", updates[0])
        async with self.sessions() as session:
            synthesis = await session.get(LaboratorySynthesis, 2)
            self.assertEqual(synthesis.laboratory_synthesis_status, LaboratorySynthesisStatus.DELETED)
        self.assertEqual((await self.client.get("/laboratory_syntheses/feed/2")).status_code, 404)

    async def test_ssr_fallbacks_form_and_no_inline_code(self):
        for path in ("/laboratory_syntheses", "/laboratory_syntheses/feed/2", "/laboratory_syntheses/draft"):
            response = await self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("/laboratory_syntheses/static/media/laboratory_syntheses_default.svg", response.text)
            self.assertNotIn("<style", response.text)
            self.assertNotIn("style=", response.text)
            self.assertNotIn("СБРОСИТЬ", response.text.upper())
            self.assertEqual("<script" in response.text, API_ENABLED)
        draft = (await self.client.get("/laboratory_syntheses/draft")).text
        self.assertIn('value="0.0"', draft)
        self.assertLess(draft.index('id="laboratory_synthesis_image"') if API_ENABLED else draft.index('class="draft-image"'), draft.index('class="draft-video"'))
        for extension in ("svg", "mp4"):
            response = await self.client.get(f"/laboratory_syntheses/static/media/laboratory_syntheses_default.{extension}")
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(response.content), 100)

    @unittest.skipIf(API_ENABLED, "В ЛР3 форма подключена к multipart API")
    async def test_two_step_draft_does_not_send_files_and_preserves_zero(self):
        await self.client.post("/laboratory_syntheses/15/delete")
        page = (await self.client.get("/laboratory_syntheses/draft")).text
        self.assertIn('type="file"', page)
        self.assertNotIn('name="laboratory_synthesis_image"', page)
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(LaboratorySynthesis).where(
                LaboratorySynthesis.laboratory_synthesis_status == LaboratorySynthesisStatus.DRAFT)), 0)
        for _ in range(2):
            response = await self.client.post("/laboratory_syntheses/draft", data={"laboratory_synthesis_name": "Новый синтез"})
            self.assertEqual(response.status_code, 303)
        async with self.sessions() as session:
            drafts = list((await session.scalars(select(LaboratorySynthesis).where(
                LaboratorySynthesis.laboratory_synthesis_status == LaboratorySynthesisStatus.DRAFT))).all())
            self.assertEqual(len(drafts), 1)
            self.assertIn("unavailable_", drafts[0].laboratory_synthesis_image_url)
        response = await self.client.post("/laboratory_syntheses/draft/publish", data={
            "laboratory_synthesis_description": "Описание", "laboratory_synthesis_duration_minutes": "90",
            "laboratory_synthesis_temperature_celsius": "0"})
        self.assertEqual(response.status_code, 303)
        feed = await self.client.get(response.headers["location"])
        self.assertEqual(feed.status_code, 200)
        self.assertIn("laboratory_syntheses_default.mp4", feed.text)

    async def test_demo_refresh_is_idempotent_and_keeps_user_uploads(self):
        with patch("laboratory_syntheses.laboratory_syntheses_seed_database.laboratory_syntheses_session_maker", self.sessions):
            await seed_database(True)
            async with self.sessions() as session:
                count = await session.scalar(select(func.count()).select_from(LaboratorySynthesis))
                demo = await session.scalar(select(LaboratorySynthesis).where(
                    LaboratorySynthesis.laboratory_synthesis_name == "Получение йодоформа"))
                demo.laboratory_synthesis_image_url = "http://localhost:9000/synthesis-media/laboratory_syntheses/custom.png"
                if hasattr(demo, "laboratory_synthesis_image_key"):
                    demo.laboratory_synthesis_image_key = "laboratory_syntheses/custom.png"
                demo.laboratory_synthesis_description = "Моё описание"
                await session.commit()
            await seed_database(True)
            async with self.sessions() as session:
                self.assertEqual(await session.scalar(select(func.count()).select_from(LaboratorySynthesis)), count)
                demo = await session.scalar(select(LaboratorySynthesis).where(
                    LaboratorySynthesis.laboratory_synthesis_name == "Получение йодоформа"))
                self.assertEqual(demo.laboratory_synthesis_description, "Моё описание")
                self.assertIn("custom.png", demo.laboratory_synthesis_image_url)
