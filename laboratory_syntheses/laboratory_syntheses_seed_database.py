"""Учебные данные; --refresh-demo обновляет только известные демонстрационные карточки."""
import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from .laboratory_syntheses_data import LABORATORY_SYNTHESES
from .laboratory_syntheses_database import laboratory_syntheses_session_maker
from .laboratory_syntheses_database_models import (
    LaboratorySynthesis, LaboratorySynthesisLike, LaboratorySynthesisStatus, LaboratorySynthesisUser,
)
from .laboratory_syntheses_media import laboratory_synthesis_media_key, laboratory_synthesis_media_url
from .laboratory_syntheses_seed_minio import prepare_demo_media


async def seed_database(refresh_demo=False):
    async with laboratory_syntheses_session_maker() as session:
        for user_id in (1, 101, 102, 103, 104, 105):
            if await session.get(LaboratorySynthesisUser, user_id) is None:
                session.add(LaboratorySynthesisUser(
                    laboratory_synthesis_user_id=user_id,
                    laboratory_synthesis_user_name=f"laboratory_synthesis_demo_{user_id}",
                ))
        await session.flush()
        for demo in LABORATORY_SYNTHESES:
            synthesis = await session.scalar(select(LaboratorySynthesis).where(
                LaboratorySynthesis.laboratory_synthesis_name == demo.laboratory_synthesis_name,
                LaboratorySynthesis.laboratory_synthesis_creator_id == 1,
            ).order_by(LaboratorySynthesis.laboratory_synthesis_id).limit(1))
            created = synthesis is None
            if created:
                status = LaboratorySynthesisStatus(demo.laboratory_synthesis_status.value)
                if status == LaboratorySynthesisStatus.DRAFT and await session.scalar(
                    select(LaboratorySynthesis.laboratory_synthesis_id).where(
                        LaboratorySynthesis.laboratory_synthesis_creator_id == 1,
                        LaboratorySynthesis.laboratory_synthesis_status == LaboratorySynthesisStatus.DRAFT,
                    ).limit(1)
                ) is not None:
                    continue
                synthesis = LaboratorySynthesis(
                    laboratory_synthesis_name=demo.laboratory_synthesis_name,
                    laboratory_synthesis_creator_id=1,
                    laboratory_synthesis_status=status,
                    laboratory_synthesis_duration_minutes=demo.laboratory_synthesis_duration_minutes,
                    laboratory_synthesis_temperature_celsius=demo.laboratory_synthesis_temperature_celsius,
                    laboratory_synthesis_formed_at=datetime.now(timezone.utc) if status == LaboratorySynthesisStatus.PUBLISHED else None,
                )
                session.add(synthesis)
            key = (getattr(synthesis, "laboratory_synthesis_image_key", None) or
                   laboratory_synthesis_media_key(synthesis.laboratory_synthesis_image_url) or "")
            # Пользовательские UUID-объекты, статусы и параметры не перезаписываем.
            is_uploaded = key.startswith("laboratory_syntheses/")
            if created or (refresh_demo and not is_uploaded):
                synthesis.laboratory_synthesis_description = demo.laboratory_synthesis_description
                for kind in ("image", "video"):
                    demo_key = getattr(demo, f"laboratory_synthesis_{kind}_key")
                    setattr(synthesis, f"laboratory_synthesis_{kind}_url", laboratory_synthesis_media_url(demo_key))
                    if hasattr(LaboratorySynthesis, f"laboratory_synthesis_{kind}_key"):
                        setattr(synthesis, f"laboratory_synthesis_{kind}_key", demo_key)
            await session.flush()
            for user_id in demo.laboratory_synthesis_liked_by_user_ids:
                like = await session.scalar(select(LaboratorySynthesisLike.laboratory_synthesis_like_id).where(
                    LaboratorySynthesisLike.laboratory_synthesis_id == synthesis.laboratory_synthesis_id,
                    LaboratorySynthesisLike.laboratory_synthesis_user_id == user_id,
                ))
                if like is None:
                    session.add(LaboratorySynthesisLike(
                        laboratory_synthesis_id=synthesis.laboratory_synthesis_id,
                        laboratory_synthesis_user_id=user_id,
                    ))
        await session.flush()
        if session.bind.dialect.name == "postgresql":
            for model, column in ((LaboratorySynthesisUser, "laboratory_synthesis_user_id"),
                                  (LaboratorySynthesis, "laboratory_synthesis_id")):
                maximum = await session.scalar(select(func.max(getattr(model, column))))
                if maximum is not None:
                    await session.execute(select(func.setval(
                        func.pg_get_serial_sequence(model.__tablename__, column), maximum, True,
                    )))
        await session.commit()


async def main(refresh_demo=False):
    await run_in_threadpool(prepare_demo_media)
    await seed_database(refresh_demo)
    print("Демоданные готовы. Пользовательские карточки и файлы сохранены.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-demo", action="store_true")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.refresh_demo))
