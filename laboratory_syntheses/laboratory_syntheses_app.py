from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .laboratory_syntheses_database import (
    get_laboratory_syntheses_database_session,
)
from .laboratory_syntheses_database_models import (
    LaboratorySynthesis,
    LaboratorySynthesisLike,
    LaboratorySynthesisStatus,
)
from .laboratory_syntheses_media import (
    LABORATORY_SYNTHESES_DIRECTORY,
    LABORATORY_SYNTHESES_DEFAULT_IMAGE_URL,
    LABORATORY_SYNTHESES_DEFAULT_VIDEO_URL,
    laboratory_synthesis_media_url,
    get_laboratory_synthesis_display_media,
    resolve_laboratory_synthesis_media,
    resolve_laboratory_syntheses_media,
)


LABORATORY_SYNTHESES_CURRENT_USER_ID = 1

app = FastAPI(
    title="Лабораторные синтезы — расчёт выхода продукта",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount(
    "/laboratory_syntheses/static",
    StaticFiles(
        directory=LABORATORY_SYNTHESES_DIRECTORY / "static",
    ),
    name="laboratory_syntheses_static",
)

laboratory_syntheses_templates = Jinja2Templates(
    directory=LABORATORY_SYNTHESES_DIRECTORY / "templates",
)

laboratory_syntheses_templates.env.globals.update(
    {
        "laboratory_syntheses_default_image_url":
            LABORATORY_SYNTHESES_DEFAULT_IMAGE_URL,
        "laboratory_syntheses_default_video_url":
            LABORATORY_SYNTHESES_DEFAULT_VIDEO_URL,
    }
)


LaboratorySynthesesDatabaseSession = Annotated[
    AsyncSession,
    Depends(get_laboratory_syntheses_database_session),
]


@app.get("/laboratory_syntheses")
async def laboratory_syntheses_catalog(
    request: Request,
    database_session: LaboratorySynthesesDatabaseSession,
    laboratory_synthesis_max_duration: Annotated[
        int | None,
        Query(ge=0, le=90),
    ] = None,
):
    laboratory_syntheses_query = (
        select(LaboratorySynthesis)
        .where(
            LaboratorySynthesis.laboratory_synthesis_status
            == LaboratorySynthesisStatus.PUBLISHED
        )
        .order_by(
            LaboratorySynthesis.laboratory_synthesis_id
        )
    )

    if laboratory_synthesis_max_duration is not None:
        laboratory_syntheses_query = (
            laboratory_syntheses_query.where(
                LaboratorySynthesis
                .laboratory_synthesis_duration_minutes
                <= laboratory_synthesis_max_duration
            )
        )

    laboratory_syntheses_result = await database_session.execute(
        laboratory_syntheses_query
    )

    laboratory_syntheses = list(
        laboratory_syntheses_result.scalars().all()
    )

    laboratory_syntheses_likes: dict[int, int] = {}

    if laboratory_syntheses:
        laboratory_synthesis_ids = [
            laboratory_synthesis.laboratory_synthesis_id
            for laboratory_synthesis in laboratory_syntheses
        ]

        laboratory_syntheses_likes_result = await database_session.execute(
            select(
                LaboratorySynthesisLike.laboratory_synthesis_id,
                func.count(
                    LaboratorySynthesisLike
                    .laboratory_synthesis_like_id
                ),
            )
            .where(
                LaboratorySynthesisLike.laboratory_synthesis_id.in_(
                    laboratory_synthesis_ids
                )
            )
            .group_by(
                LaboratorySynthesisLike.laboratory_synthesis_id
            )
        )

        laboratory_syntheses_likes = {
            laboratory_synthesis_id: laboratory_synthesis_likes
            for (
                laboratory_synthesis_id,
                laboratory_synthesis_likes,
            ) in laboratory_syntheses_likes_result.all()
        }

    for laboratory_synthesis in laboratory_syntheses:
        laboratory_syntheses_likes.setdefault(
            laboratory_synthesis.laboratory_synthesis_id,
            0,
        )

    return laboratory_syntheses_templates.TemplateResponse(
        request=request,
        name="laboratory_syntheses_catalog.html",
        context={
            "laboratory_syntheses_active_page": "catalog",
            "laboratory_syntheses": laboratory_syntheses,
            "laboratory_syntheses_display_media": await resolve_laboratory_syntheses_media(laboratory_syntheses),
            "laboratory_syntheses_likes":
                laboratory_syntheses_likes,
            "laboratory_synthesis_max_duration":
                laboratory_synthesis_max_duration,
        },
    )


@app.get("/laboratory_syntheses/draft")
async def laboratory_syntheses_draft(
    request: Request,
    database_session: LaboratorySynthesesDatabaseSession,
):
    laboratory_synthesis = await database_session.scalar(
        select(LaboratorySynthesis)
        .where(
            LaboratorySynthesis.laboratory_synthesis_creator_id
            == LABORATORY_SYNTHESES_CURRENT_USER_ID,
            LaboratorySynthesis.laboratory_synthesis_status
            == LaboratorySynthesisStatus.DRAFT,
        )
        .limit(1)
    )

    return laboratory_syntheses_templates.TemplateResponse(
        request=request,
        name="laboratory_syntheses_draft.html",
        context={
            "laboratory_syntheses_active_page": "draft",
            "laboratory_synthesis": laboratory_synthesis,
            "laboratory_synthesis_display_media": await resolve_laboratory_synthesis_media(laboratory_synthesis),
        },
    )


@app.get("/laboratory_syntheses/feed")
@app.get("/laboratory_syntheses/feed/{laboratory_synthesis_id}")
async def laboratory_syntheses_feed(
    request: Request,
    database_session: LaboratorySynthesesDatabaseSession,
    laboratory_synthesis_id: int | None = None,
    laboratory_synthesis_next: Annotated[
        bool,
        Query(alias="next"),
    ] = False,
):
    published_condition = (
        LaboratorySynthesis.laboratory_synthesis_status
        == LaboratorySynthesisStatus.PUBLISHED
    )

    if laboratory_synthesis_id is None:
        laboratory_synthesis = await database_session.scalar(
            select(LaboratorySynthesis)
            .where(published_condition)
            .order_by(
                LaboratorySynthesis.laboratory_synthesis_id
            )
            .limit(1)
        )

    elif laboratory_synthesis_next:
        # Следующая карточка выбирается запросом к БД, а не через id + 1.
        # Поэтому удалённые записи и пропуски в последовательности id
        # автоматически пропускаются.
        laboratory_synthesis = await database_session.scalar(
            select(LaboratorySynthesis)
            .where(
                published_condition,
                LaboratorySynthesis.laboratory_synthesis_id
                > laboratory_synthesis_id,
            )
            .order_by(
                LaboratorySynthesis.laboratory_synthesis_id
            )
            .limit(1)
        )

        if laboratory_synthesis is None:
            laboratory_synthesis = await database_session.scalar(
                select(LaboratorySynthesis)
                .where(published_condition)
                .order_by(
                    LaboratorySynthesis.laboratory_synthesis_id
                )
                .limit(1)
            )

    else:
        laboratory_synthesis = await database_session.scalar(
            select(LaboratorySynthesis)
            .where(
                published_condition,
                LaboratorySynthesis.laboratory_synthesis_id
                == laboratory_synthesis_id,
            )
            .limit(1)
        )

    if laboratory_synthesis is None:
        raise HTTPException(
            status_code=404,
            detail="Опубликованный лабораторный синтез не найден",
        )

    laboratory_synthesis_likes = await database_session.scalar(
        select(
            func.count(
                LaboratorySynthesisLike
                .laboratory_synthesis_like_id
            )
        )
        .where(
            LaboratorySynthesisLike.laboratory_synthesis_id
            == laboratory_synthesis.laboratory_synthesis_id
        )
    )

    laboratory_syntheses_count = await database_session.scalar(
        select(func.count(LaboratorySynthesis.laboratory_synthesis_id))
        .where(published_condition)
    )

    laboratory_synthesis_position = await database_session.scalar(
        select(func.count(LaboratorySynthesis.laboratory_synthesis_id))
        .where(
            published_condition,
            LaboratorySynthesis.laboratory_synthesis_id
            <= laboratory_synthesis.laboratory_synthesis_id,
        )
    )

    return laboratory_syntheses_templates.TemplateResponse(
        request=request,
        name="laboratory_syntheses_feed.html",
        context={
            "laboratory_syntheses_active_page": "feed",
            "laboratory_synthesis": laboratory_synthesis,
            "laboratory_synthesis_display_media": await resolve_laboratory_synthesis_media(laboratory_synthesis),
            "laboratory_synthesis_likes":
                laboratory_synthesis_likes or 0,
            "laboratory_synthesis_position":
                laboratory_synthesis_position or 1,
            "laboratory_syntheses_count":
                laboratory_syntheses_count or 0,
        },
    )


@app.post("/laboratory_syntheses/draft")
async def laboratory_syntheses_create_draft(
    database_session: LaboratorySynthesesDatabaseSession,
    laboratory_synthesis_name: Annotated[
        str,
        Form(min_length=1, max_length=120),
    ],
):
    existing_draft = await database_session.scalar(
        select(LaboratorySynthesis)
        .where(
            LaboratorySynthesis.laboratory_synthesis_creator_id
            == LABORATORY_SYNTHESES_CURRENT_USER_ID,
            LaboratorySynthesis.laboratory_synthesis_status
            == LaboratorySynthesisStatus.DRAFT,
        )
        .limit(1)
    )

    if existing_draft is None:
        laboratory_synthesis = LaboratorySynthesis(
            laboratory_synthesis_name=laboratory_synthesis_name,
            laboratory_synthesis_description=None,
            laboratory_synthesis_status=LaboratorySynthesisStatus.DRAFT,
            laboratory_synthesis_image_url=(
                laboratory_synthesis_media_url("unavailable_laboratory_synthesis_image.jpg")
            ),
            laboratory_synthesis_video_url=(
                laboratory_synthesis_media_url("unavailable_laboratory_synthesis_video.mp4")
            ),
            laboratory_synthesis_duration_minutes=None,
            laboratory_synthesis_temperature_celsius=None,
            laboratory_synthesis_creator_id=(
                LABORATORY_SYNTHESES_CURRENT_USER_ID
            ),
        )

        database_session.add(laboratory_synthesis)
        await database_session.commit()

    return RedirectResponse(
        url="/laboratory_syntheses/draft",
        status_code=303,
    )


@app.post("/laboratory_syntheses/draft/publish")
async def laboratory_syntheses_publish_draft(
    database_session: LaboratorySynthesesDatabaseSession,
    laboratory_synthesis_description: Annotated[
        str,
        Form(min_length=1),
    ],
    laboratory_synthesis_duration_minutes: Annotated[
        int,
        Form(ge=1, le=90),
    ],
    laboratory_synthesis_temperature_celsius: Annotated[
        float,
        Form(ge=-273.15, allow_inf_nan=False),
    ],
):
    laboratory_synthesis = await database_session.scalar(
        select(LaboratorySynthesis)
        .where(
            LaboratorySynthesis.laboratory_synthesis_creator_id
            == LABORATORY_SYNTHESES_CURRENT_USER_ID,
            LaboratorySynthesis.laboratory_synthesis_status
            == LaboratorySynthesisStatus.DRAFT,
        )
        .limit(1)
    )

    if laboratory_synthesis is None:
        raise HTTPException(
            status_code=404,
            detail="Черновик лабораторного синтеза отсутствует",
        )

    laboratory_synthesis.laboratory_synthesis_description = (
        laboratory_synthesis_description
    )

    laboratory_synthesis.laboratory_synthesis_duration_minutes = (
        laboratory_synthesis_duration_minutes
    )

    laboratory_synthesis.laboratory_synthesis_temperature_celsius = (
        laboratory_synthesis_temperature_celsius
    )

    laboratory_synthesis.laboratory_synthesis_status = (
        LaboratorySynthesisStatus.PUBLISHED
    )

    laboratory_synthesis.laboratory_synthesis_formed_at = (
        datetime.now(timezone.utc)
    )

    await database_session.commit()

    return RedirectResponse(
        url=(
            "/laboratory_syntheses/feed/"
            f"{laboratory_synthesis.laboratory_synthesis_id}"
        ),
        status_code=303,
    )


@app.post(
    "/laboratory_syntheses/{laboratory_synthesis_id}/delete"
)
async def laboratory_syntheses_delete(
    laboratory_synthesis_id: int,
    database_session: LaboratorySynthesesDatabaseSession,
):
    """Для ЛР2 удаление выполняется прямым SQL UPDATE, без ORM."""
    current_user_id = LABORATORY_SYNTHESES_CURRENT_USER_ID
    parameters = {
        "laboratory_synthesis_id": laboratory_synthesis_id,
        "laboratory_synthesis_creator_id": current_user_id,
    }
    result = await database_session.execute(
        text("""
            UPDATE laboratory_syntheses
            SET laboratory_synthesis_status = 'deleted'
            WHERE laboratory_synthesis_id = :laboratory_synthesis_id
              AND laboratory_synthesis_creator_id = :laboratory_synthesis_creator_id
              AND laboratory_synthesis_status <> 'deleted'
        """),
        parameters,
    )
    if result.rowcount == 0:
        owner = await database_session.scalar(
            text("""
                SELECT laboratory_synthesis_creator_id
                FROM laboratory_syntheses
                WHERE laboratory_synthesis_id = :laboratory_synthesis_id
                  AND laboratory_synthesis_status <> 'deleted'
            """),
            {"laboratory_synthesis_id": laboratory_synthesis_id},
        )
        await database_session.rollback()
        if owner is not None and owner != current_user_id:
            raise HTTPException(403, "Удалять можно только собственные синтезы")
        raise HTTPException(404, "Лабораторный синтез не найден")
    await database_session.commit()
    return RedirectResponse(url="/laboratory_syntheses", status_code=303)


laboratory_syntheses_templates.env.globals.update({
    "laboratory_syntheses_database_enabled": True,
    "laboratory_syntheses_api_enabled": False,
    "laboratory_syntheses_current_user_id": 1,
})
