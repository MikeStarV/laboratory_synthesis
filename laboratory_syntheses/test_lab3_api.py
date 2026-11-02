"""Контракт ЛР3 и транзакционность создания без рабочих PostgreSQL/MinIO."""

import asyncio
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from laboratory_syntheses.laboratory_syntheses_app import app
from laboratory_syntheses import laboratory_syntheses_api as api
from laboratory_syntheses.laboratory_syntheses_current_user import LaboratorySynthesisCurrentUser
from laboratory_syntheses.laboratory_syntheses_database_models import LaboratorySynthesisStatus
from laboratory_syntheses.laboratory_syntheses_database_models import LaboratorySynthesis
from laboratory_syntheses.laboratory_syntheses_serializers import (
    LaboratorySynthesisPublicationInput,
)


def test_openapi_has_ten_methods_and_two_feed_routes():
    routes = [
        route for route in app.routes
        if route.path.startswith("/api/") and route.path not in
        {"/api/docs", "/api/openapi.json", "/api/redoc"}
    ]
    assert len(routes) == 11
    assert len({route.endpoint for route in routes}) == 10
    spec = app.openapi()
    create = spec["paths"]["/api/laboratory_syntheses"]["post"]
    body_ref = create["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    props = spec["components"]["schemas"][body_ref.rsplit("/", 1)[1]]["properties"]
    assert set(props) == {"laboratory_synthesis_name", "laboratory_synthesis_image", "laboratory_synthesis_video"}
    publish = spec["paths"]["/api/laboratory_syntheses/draft/publication"]["put"]
    assert publish["requestBody"]["required"]


def test_invalid_fields_and_auth_stubs():
    for stub in (api.laboratory_synthesis_users_login, api.laboratory_synthesis_users_logout):
        with pytest.raises(HTTPException) as error:
            asyncio.run(stub())
        assert error.value.status_code == 501


def test_publication_input_rejects_system_fields():
    from pydantic import ValidationError
    try:
        LaboratorySynthesisPublicationInput(
            laboratory_synthesis_description="Описание",
            laboratory_synthesis_duration_minutes=20,
            laboratory_synthesis_temperature_celsius=20,
            laboratory_synthesis_status=LaboratorySynthesisStatus.PUBLISHED,
        )
    except ValidationError:
        pass
    else:
        assert False, "Системное поле было принято"


class FakeSession:
    def __init__(self, draft=None):
        self.draft = draft
        self.added = None
        self.rolled_back = False
        self.committed = False
        self.calls = 0

    async def scalar(self, query):
        self.calls += 1
        return object() if self.calls == 1 else self.draft

    def add(self, value):
        self.added = value

    async def rollback(self):
        self.rolled_back = True

    async def commit(self):
        self.committed = True
        if self.added is not None:
            self.added.laboratory_synthesis_id = 999


class FakeStorage:
    def __init__(self, fail=False):
        self.fail = fail
        self.put_keys = []
        self.deleted_keys = []

    def put(self, key, payload, content_type):
        self.put_keys.append(key)
        if self.fail and len(self.put_keys) == 2:
            raise OSError("MinIO недоступен")

    def delete_safely(self, key):
        self.deleted_keys.append(key)


def test_create_rolls_back_and_cleans_uploaded_files(monkeypatch):
    async def direct(call, *args):
        return call(*args)
    monkeypatch.setattr(api, "run_in_threadpool", direct)

    class Request:
        async def form(self):
            return {"laboratory_synthesis_name": "Тест", "laboratory_synthesis_image": 1,
                    "laboratory_synthesis_video": 1}

    async def create(session, storage):
        def upload(payload, filename):
            file = SpooledTemporaryFile()
            file.write(payload)
            file.seek(0)
            return UploadFile(file, filename=filename)
        return await api.laboratory_syntheses_save_draft(
            Request(), session, LaboratorySynthesisCurrentUser(1), storage, "Тест",
            upload(b"\x89PNG\r\n\x1a\nimage", "photo.png"),
            upload(b"\x00\x00\x00\x18ftypisomvideo", "video.mp4"),
        )

    session, storage = FakeSession(), FakeStorage(fail=True)
    with pytest.raises(HTTPException) as error:
        asyncio.run(create(session, storage))
    assert error.value.status_code == 503
    assert session.rolled_back and not session.committed
    assert storage.deleted_keys == storage.put_keys

    session = FakeSession(draft=object())
    storage = FakeStorage()
    with pytest.raises(HTTPException) as error:
        asyncio.run(create(session, storage))
    assert error.value.status_code == 409
    assert storage.put_keys == []


def test_publication_uses_current_users_draft_and_cannot_repeat(monkeypatch):
    async def response(session, author, synthesis_id):
        return {"laboratory_synthesis_id": synthesis_id}
    monkeypatch.setattr(api, "laboratory_synthesis_response", response)
    draft = LaboratorySynthesis(
        laboratory_synthesis_id=42,
        laboratory_synthesis_creator_id=1,
        laboratory_synthesis_status=LaboratorySynthesisStatus.DRAFT,
        laboratory_synthesis_name="Тест",
        laboratory_synthesis_image_key="photo.png",
        laboratory_synthesis_video_key="video.mp4",
    )
    body = LaboratorySynthesisPublicationInput(
        laboratory_synthesis_description="Описание",
        laboratory_synthesis_duration_minutes=25,
        laboratory_synthesis_temperature_celsius=22,
    )
    session = FakeSession(draft=draft)
    result = asyncio.run(api.laboratory_syntheses_publish(
        session, LaboratorySynthesisCurrentUser(1), body,
    ))
    assert result["laboratory_synthesis_id"] == 42
    assert session.committed
    assert draft.laboratory_synthesis_status == LaboratorySynthesisStatus.PUBLISHED
    assert draft.laboratory_synthesis_description == "Описание"

    with pytest.raises(HTTPException) as error:
        asyncio.run(api.laboratory_syntheses_publish(
            FakeSession(), LaboratorySynthesisCurrentUser(1), body,
        ))
    assert error.value.status_code == 409


def test_foreign_synthesis_cannot_be_deleted():
    foreign = LaboratorySynthesis(
        laboratory_synthesis_id=99,
        laboratory_synthesis_creator_id=2,
        laboratory_synthesis_status=LaboratorySynthesisStatus.PUBLISHED,
    )

    class Session:
        async def scalar(self, query):
            return foreign

    with pytest.raises(HTTPException) as error:
        asyncio.run(api.laboratory_syntheses_remove(
            99, Session(), LaboratorySynthesisCurrentUser(1),
        ))
    assert error.value.status_code == 403
    assert foreign.laboratory_synthesis_status == LaboratorySynthesisStatus.PUBLISHED
