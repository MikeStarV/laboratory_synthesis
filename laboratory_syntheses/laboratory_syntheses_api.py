"""JSON API ЛР3: каталог, лента, черновик, публикация, удаление и лайки."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import (
    APIRouter, Body, Depends, File, Form, HTTPException, Path, Query, Request,
    Response, UploadFile,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .laboratory_syntheses_current_user import (
    LaboratorySynthesisCurrentUser, get_laboratory_synthesis_current_user,
)
from .laboratory_syntheses_database import get_laboratory_syntheses_database_session
from .laboratory_syntheses_database_models import (
    LaboratorySynthesis, LaboratorySynthesisLike, LaboratorySynthesisStatus,
    LaboratorySynthesisUser,
)
from .laboratory_syntheses_serializers import (
    LaboratorySynthesisDraftInput, LaboratorySynthesisLikeInput,
    LaboratorySynthesisPublicationInput, LaboratorySynthesisRegistrationInput,
    LaboratorySynthesisResponse, LaboratorySynthesisUserResponse,
)
from .laboratory_syntheses_storage import (
    LaboratorySynthesisMediaStorage, get_laboratory_synthesis_media_storage,
    laboratory_synthesis_object_url, read_laboratory_synthesis_upload,
)


laboratory_syntheses_api = APIRouter(
    prefix="/api/laboratory_syntheses", tags=["Лабораторные синтезы"],
)
laboratory_synthesis_users_api = APIRouter(
    prefix="/api/laboratory_synthesis_users", tags=["Пользователи синтезов"],
)
LaboratorySynthesesSession = Annotated[
    AsyncSession, Depends(get_laboratory_syntheses_database_session),
]
LaboratorySynthesisAuthor = Annotated[
    LaboratorySynthesisCurrentUser, Depends(get_laboratory_synthesis_current_user),
]
LaboratorySynthesisStorage = Annotated[
    LaboratorySynthesisMediaStorage, Depends(get_laboratory_synthesis_media_storage),
]
LaboratorySynthesisId = Annotated[int, Path(ge=1)]


def laboratory_syntheses_response_query(author: LaboratorySynthesisCurrentUser):
    """Один SQL-запрос: карточка, вложенный автор, число лайков, свой лайк."""
    likes = (
        select(
            LaboratorySynthesisLike.laboratory_synthesis_id,
            func.count().label("laboratory_synthesis_likes_count"),
        )
        .group_by(LaboratorySynthesisLike.laboratory_synthesis_id).subquery()
    )
    liked = (
        select(LaboratorySynthesisLike.laboratory_synthesis_like_id)
        .where(
            LaboratorySynthesisLike.laboratory_synthesis_id
            == LaboratorySynthesis.laboratory_synthesis_id,
            LaboratorySynthesisLike.laboratory_synthesis_user_id
            == author.laboratory_synthesis_user_id,
        )
        .correlate(LaboratorySynthesis).exists()
    )
    return (
        select(
            LaboratorySynthesis, LaboratorySynthesisUser,
            func.coalesce(likes.c.laboratory_synthesis_likes_count, 0), liked,
        )
        .join(
            LaboratorySynthesisUser,
            LaboratorySynthesisUser.laboratory_synthesis_user_id
            == LaboratorySynthesis.laboratory_synthesis_creator_id,
        )
        .outerjoin(
            likes,
            likes.c.laboratory_synthesis_id
            == LaboratorySynthesis.laboratory_synthesis_id,
        )
    )


def serialize_laboratory_synthesis(row, author: LaboratorySynthesisCurrentUser):
    synthesis, creator, likes_count, liked = row
    fields = {
        field: getattr(synthesis, field)
        for field in LaboratorySynthesisResponse.model_fields
        if hasattr(LaboratorySynthesis, field)
        and field != "laboratory_synthesis_creator"
    }
    for kind in ("image", "video"):
        key = getattr(synthesis, f"laboratory_synthesis_{kind}_key")
        if key:
            fields[f"laboratory_synthesis_{kind}_url"] = (
                laboratory_synthesis_object_url(key)
            )
    return LaboratorySynthesisResponse(
        **fields,
        laboratory_synthesis_creator=LaboratorySynthesisUserResponse.model_validate(
            creator,
        ),
        laboratory_synthesis_is_creator=int(
            synthesis.laboratory_synthesis_creator_id
            == author.laboratory_synthesis_user_id
        ),
        laboratory_synthesis_liked=int(liked),
        laboratory_synthesis_likes_count=likes_count,
    )


async def laboratory_synthesis_response(session, author, synthesis_id):
    rows = await session.execute(
        laboratory_syntheses_response_query(author).where(
            LaboratorySynthesis.laboratory_synthesis_id == synthesis_id,
            LaboratorySynthesis.laboratory_synthesis_status
            != LaboratorySynthesisStatus.DELETED,
        ),
    )
    row = rows.first()
    if row is None:
        raise HTTPException(404, "Лабораторный синтез не найден")
    return serialize_laboratory_synthesis(row, author)


async def laboratory_synthesis_author_record(session, author):
    # Блокировка пользователя сериализует параллельные сохранения черновика.
    user = await session.scalar(
        select(LaboratorySynthesisUser).where(
            LaboratorySynthesisUser.laboratory_synthesis_user_id
            == author.laboratory_synthesis_user_id,
        ).with_for_update(),
    )
    if user is None:
        raise HTTPException(
            409, "Текущий пользователь отсутствует в БД. Запустите заполнение демоданных.",
        )
    return user


async def owned_laboratory_synthesis(session, author, synthesis_id):
    synthesis = await session.scalar(
        select(LaboratorySynthesis).where(
            LaboratorySynthesis.laboratory_synthesis_id == synthesis_id,
            LaboratorySynthesis.laboratory_synthesis_status
            != LaboratorySynthesisStatus.DELETED,
        ).with_for_update(),
    )
    if synthesis is None:
        raise HTTPException(404, "Лабораторный синтез не найден")
    if synthesis.laboratory_synthesis_creator_id != author.laboratory_synthesis_user_id:
        raise HTTPException(403, "Изменять можно только собственные синтезы")
    return synthesis


@laboratory_syntheses_api.get("", response_model=list[LaboratorySynthesisResponse])
async def laboratory_syntheses_list(
    session: LaboratorySynthesesSession,
    author: LaboratorySynthesisAuthor,
    laboratory_synthesis_max_duration: Annotated[
        int | None, Query(ge=0, le=90),
    ] = None,
):
    query = laboratory_syntheses_response_query(author).where(
        LaboratorySynthesis.laboratory_synthesis_status
        == LaboratorySynthesisStatus.PUBLISHED,
    )
    if laboratory_synthesis_max_duration is not None:
        query = query.where(
            LaboratorySynthesis.laboratory_synthesis_duration_minutes
            <= laboratory_synthesis_max_duration,
        )
    rows = await session.execute(
        query.order_by(LaboratorySynthesis.laboratory_synthesis_id),
    )
    return [serialize_laboratory_synthesis(row, author) for row in rows]


@laboratory_syntheses_api.get("/draft", response_model=LaboratorySynthesisResponse)
async def laboratory_syntheses_get_draft(
    session: LaboratorySynthesesSession, author: LaboratorySynthesisAuthor,
):
    rows = await session.execute(
        laboratory_syntheses_response_query(author).where(
            LaboratorySynthesis.laboratory_synthesis_creator_id
            == author.laboratory_synthesis_user_id,
            LaboratorySynthesis.laboratory_synthesis_status
            == LaboratorySynthesisStatus.DRAFT,
        ),
    )
    row = rows.first()
    if row is None:
        raise HTTPException(404, "Черновик лабораторного синтеза отсутствует")
    return serialize_laboratory_synthesis(row, author)


@laboratory_syntheses_api.get("/feed", response_model=LaboratorySynthesisResponse)
@laboratory_syntheses_api.get(
    "/feed/{laboratory_synthesis_id}", response_model=LaboratorySynthesisResponse,
)
async def laboratory_syntheses_get_feed(
    session: LaboratorySynthesesSession,
    author: LaboratorySynthesisAuthor,
    laboratory_synthesis_id: int | None = None,
    laboratory_synthesis_next: Annotated[bool, Query(alias="next")] = False,
):
    if laboratory_synthesis_id is not None and laboratory_synthesis_id < 1:
        raise HTTPException(422, "Идентификатор синтеза должен быть положительным")
    published = laboratory_syntheses_response_query(author).where(
        LaboratorySynthesis.laboratory_synthesis_status
        == LaboratorySynthesisStatus.PUBLISHED,
    )
    query = published
    if laboratory_synthesis_id is not None:
        query = query.where(
            LaboratorySynthesis.laboratory_synthesis_id > laboratory_synthesis_id
            if laboratory_synthesis_next
            else LaboratorySynthesis.laboratory_synthesis_id == laboratory_synthesis_id,
        )
    rows = await session.execute(
        query.order_by(LaboratorySynthesis.laboratory_synthesis_id).limit(1),
    )
    row = rows.first()
    if row is None and laboratory_synthesis_next:
        rows = await session.execute(
            published.order_by(LaboratorySynthesis.laboratory_synthesis_id).limit(1),
        )
        row = rows.first()
    if row is None:
        raise HTTPException(404, "Опубликованный лабораторный синтез не найден")
    return serialize_laboratory_synthesis(row, author)


@laboratory_syntheses_api.post(
    "", response_model=LaboratorySynthesisResponse, status_code=201,
    responses={200: {"description": "Обновлён уже существующий черновик"}},
)
async def laboratory_syntheses_save_draft(
    request: Request,
    response: Response,
    session: LaboratorySynthesesSession,
    author: LaboratorySynthesisAuthor,
    storage: LaboratorySynthesisStorage,
    laboratory_synthesis_name: Annotated[str, Form(min_length=1, max_length=120)],
    laboratory_synthesis_description: Annotated[
        str, Form(min_length=1, max_length=5000),
    ],
    laboratory_synthesis_duration_minutes: Annotated[int, Form(ge=1, le=90)],
    laboratory_synthesis_temperature_celsius: Annotated[
        float, Form(ge=-273.15, allow_inf_nan=False),
    ],
    laboratory_synthesis_image: Annotated[UploadFile | None, File()] = None,
    laboratory_synthesis_video: Annotated[UploadFile | None, File()] = None,
):
    form = await request.form()
    allowed = set(LaboratorySynthesisDraftInput.model_fields) | {
        "laboratory_synthesis_image", "laboratory_synthesis_video",
    }
    if extra := set(form) - allowed:
        raise HTTPException(422, f"Недопустимые поля: {', '.join(sorted(extra))}")
    try:
        draft_fields = LaboratorySynthesisDraftInput(
            laboratory_synthesis_name=laboratory_synthesis_name,
            laboratory_synthesis_description=laboratory_synthesis_description,
            laboratory_synthesis_duration_minutes=laboratory_synthesis_duration_minutes,
            laboratory_synthesis_temperature_celsius=(
                laboratory_synthesis_temperature_celsius
            ),
        )
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error

    await laboratory_synthesis_author_record(session, author)
    draft = await session.scalar(
        select(LaboratorySynthesis).where(
            LaboratorySynthesis.laboratory_synthesis_creator_id
            == author.laboratory_synthesis_user_id,
            LaboratorySynthesis.laboratory_synthesis_status
            == LaboratorySynthesisStatus.DRAFT,
        ).with_for_update(),
    )
    created = draft is None
    # При редактировании можно оставить уже загруженные файлы.
    # Для нового или перенесённого из ЛР2 черновика нужны оба файла.
    uploads = {}
    for kind, upload in (("image", laboratory_synthesis_image),
                         ("video", laboratory_synthesis_video)):
        if upload is not None:
            uploads[kind] = await read_laboratory_synthesis_upload(
                upload, video=kind == "video",
            )
        elif draft is None or not getattr(draft, f"laboratory_synthesis_{kind}_key"):
            raise HTTPException(422, "Для черновика необходимо загрузить фото и видео")
    old_keys = []
    if draft is None:
        draft = LaboratorySynthesis(
            laboratory_synthesis_creator_id=author.laboratory_synthesis_user_id,
            laboratory_synthesis_status=LaboratorySynthesisStatus.DRAFT,
            **draft_fields.model_dump(),
        )
        session.add(draft)
    else:
        old_keys = [getattr(draft, f"laboratory_synthesis_{kind}_key")
                    for kind in uploads]
        for field, value in draft_fields.model_dump().items():
            setattr(draft, field, value)
    try:
        for kind, uploaded in uploads.items():
            await run_in_threadpool(storage.put, *uploaded)
            setattr(draft, f"laboratory_synthesis_{kind}_key", uploaded[0])
            setattr(draft, f"laboratory_synthesis_{kind}_url",
                    laboratory_synthesis_object_url(uploaded[0]))
        await session.commit()
    except (BotoCoreError, ClientError, OSError, SQLAlchemyError) as error:
        await session.rollback()
        for uploaded in uploads.values():
            await run_in_threadpool(storage.delete_safely, uploaded[0])
        if isinstance(error, IntegrityError):
            raise HTTPException(409, "Конфликт сохранения черновика, повторите запрос") from error
        raise HTTPException(503, "Не удалось сохранить синтез в БД или MinIO") from error
    for key in old_keys:
        if key:
            await run_in_threadpool(storage.delete_safely, key)
    response.status_code = 201 if created else 200
    return await laboratory_synthesis_response(
        session, author, draft.laboratory_synthesis_id,
    )


@laboratory_syntheses_api.put(
    "/{laboratory_synthesis_id}/publication",
    response_model=LaboratorySynthesisResponse,
)
async def laboratory_syntheses_publish(
    laboratory_synthesis_id: LaboratorySynthesisId,
    session: LaboratorySynthesesSession,
    author: LaboratorySynthesisAuthor,
    publication: Annotated[
        LaboratorySynthesisPublicationInput | None, Body(),
    ] = None,
):
    synthesis = await owned_laboratory_synthesis(
        session, author, laboratory_synthesis_id,
    )
    if synthesis.laboratory_synthesis_status != LaboratorySynthesisStatus.DRAFT:
        raise HTTPException(409, "Опубликовать можно только черновик")
    required = (
        synthesis.laboratory_synthesis_name,
        synthesis.laboratory_synthesis_description,
        synthesis.laboratory_synthesis_duration_minutes,
        synthesis.laboratory_synthesis_image_key,
        synthesis.laboratory_synthesis_video_key,
    )
    if not all(required) or synthesis.laboratory_synthesis_temperature_celsius is None:
        raise HTTPException(409, "Перед публикацией заполните все поля и загрузите медиа")
    try:
        LaboratorySynthesisDraftInput(**{
            field: getattr(synthesis, field)
            for field in LaboratorySynthesisDraftInput.model_fields
        })
    except ValidationError as error:
        raise HTTPException(409, "Черновик содержит некорректные поля") from error
    synthesis.laboratory_synthesis_status = LaboratorySynthesisStatus.PUBLISHED
    synthesis.laboratory_synthesis_formed_at = datetime.now(timezone.utc)
    await session.commit()
    return await laboratory_synthesis_response(session, author, laboratory_synthesis_id)


@laboratory_syntheses_api.delete("/{laboratory_synthesis_id}", status_code=204)
async def laboratory_syntheses_remove(
    laboratory_synthesis_id: LaboratorySynthesisId,
    session: LaboratorySynthesesSession,
    author: LaboratorySynthesisAuthor,
):
    synthesis = await owned_laboratory_synthesis(
        session, author, laboratory_synthesis_id,
    )
    synthesis.laboratory_synthesis_status = LaboratorySynthesisStatus.DELETED
    await session.commit()
    return Response(status_code=204)


@laboratory_syntheses_api.post(
    "/{laboratory_synthesis_id}/likes", response_model=LaboratorySynthesisResponse,
)
async def laboratory_syntheses_set_like(
    laboratory_synthesis_id: LaboratorySynthesisId,
    body: LaboratorySynthesisLikeInput,
    session: LaboratorySynthesesSession,
    author: LaboratorySynthesisAuthor,
):
    synthesis = await session.scalar(
        select(LaboratorySynthesis).where(
            LaboratorySynthesis.laboratory_synthesis_id == laboratory_synthesis_id,
            LaboratorySynthesis.laboratory_synthesis_status
            == LaboratorySynthesisStatus.PUBLISHED,
        ).with_for_update(),
    )
    if synthesis is None:
        raise HTTPException(404, "Опубликованный лабораторный синтез не найден")
    if await session.get(LaboratorySynthesisUser, author.laboratory_synthesis_user_id) is None:
        raise HTTPException(409, "Текущий пользователь отсутствует в БД")
    like = await session.scalar(
        select(LaboratorySynthesisLike).where(
            LaboratorySynthesisLike.laboratory_synthesis_id == laboratory_synthesis_id,
            LaboratorySynthesisLike.laboratory_synthesis_user_id
            == author.laboratory_synthesis_user_id,
        ),
    )
    if body.laboratory_synthesis_liked == 1 and like is None:
        session.add(LaboratorySynthesisLike(
            laboratory_synthesis_id=laboratory_synthesis_id,
            laboratory_synthesis_user_id=author.laboratory_synthesis_user_id,
        ))
    elif body.laboratory_synthesis_liked == 0 and like is not None:
        await session.delete(like)
    await session.commit()
    return await laboratory_synthesis_response(session, author, laboratory_synthesis_id)


def hash_laboratory_synthesis_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 600_000,
    ).hex()
    return "pbkdf2_sha256$600000$" + salt + "$" + digest


@laboratory_synthesis_users_api.post(
    "", response_model=LaboratorySynthesisUserResponse, status_code=201,
)
async def laboratory_synthesis_users_register(
    body: LaboratorySynthesisRegistrationInput, session: LaboratorySynthesesSession,
):
    password_hash = await run_in_threadpool(
        hash_laboratory_synthesis_password,
        body.laboratory_synthesis_user_password.get_secret_value(),
    )
    user = LaboratorySynthesisUser(
        laboratory_synthesis_user_name=body.laboratory_synthesis_user_name,
        laboratory_synthesis_user_password_hash=password_hash,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(409, "Такое имя пользователя уже зарегистрировано") from error
    return user


@laboratory_synthesis_users_api.post("/login", status_code=501)
async def laboratory_synthesis_users_login():
    raise HTTPException(501, "Заглушка ЛР3. Аутентификация появится в ЛР4.")


@laboratory_synthesis_users_api.post("/logout", status_code=501)
async def laboratory_synthesis_users_logout():
    raise HTTPException(501, "Заглушка ЛР3. Завершение сессии появится в ЛР4.")
