"""Добавить учебные записи, не удаляя и не изменяя существующие синтезы."""

import asyncio
import mimetypes
from pathlib import Path

from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from .laboratory_syntheses_current_user import (
    get_laboratory_synthesis_current_user,
)
from .laboratory_syntheses_data import LABORATORY_SYNTHESES
from .laboratory_syntheses_database import laboratory_syntheses_session_maker
from .laboratory_syntheses_database_models import (
    LaboratorySynthesis, LaboratorySynthesisStatus, LaboratorySynthesisUser,
)
from .laboratory_syntheses_storage import (
    get_laboratory_synthesis_media_storage, laboratory_synthesis_object_url,
)


async def main() -> None:
    examples = Path(__file__).resolve().parents[1] / "examples"
    storage = get_laboratory_synthesis_media_storage()
    media = {}
    for kind, filename in [
        ("image", "laboratory_synthesis_preview.png"),
        ("video", "laboratory_synthesis_preview.mp4"),
    ]:
        path = examples / filename
        key = f"laboratory_syntheses_demo/{filename}"
        await run_in_threadpool(
            storage.put, key, path.read_bytes(),
            mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )
        media[kind] = key

    async with laboratory_syntheses_session_maker() as session:
        author_id = get_laboratory_synthesis_current_user().laboratory_synthesis_user_id
        if await session.get(LaboratorySynthesisUser, author_id) is None:
            session.add(LaboratorySynthesisUser(
                laboratory_synthesis_user_id=author_id,
                laboratory_synthesis_user_name="laboratory_synthesis_author",
            ))
            await session.flush()
        for demo in LABORATORY_SYNTHESES:
            if demo.laboratory_synthesis_status.value != "published":
                continue
            existing = await session.scalar(
                select(LaboratorySynthesis).where(
                    LaboratorySynthesis.laboratory_synthesis_name
                    == demo.laboratory_synthesis_name,
                ),
            )
            if existing is not None:
                continue
            session.add(LaboratorySynthesis(
                laboratory_synthesis_name=demo.laboratory_synthesis_name,
                laboratory_synthesis_description=demo.laboratory_synthesis_description,
                laboratory_synthesis_duration_minutes=demo.laboratory_synthesis_duration_minutes,
                laboratory_synthesis_temperature_celsius=demo.laboratory_synthesis_temperature_celsius,
                laboratory_synthesis_status=LaboratorySynthesisStatus.PUBLISHED,
                laboratory_synthesis_creator_id=author_id,
                laboratory_synthesis_image_key=media["image"],
                laboratory_synthesis_video_key=media["video"],
                laboratory_synthesis_image_url=laboratory_synthesis_object_url(media["image"]),
                laboratory_synthesis_video_url=laboratory_synthesis_object_url(media["video"]),
                laboratory_synthesis_formed_at=func.now(),
            ))
        await session.flush()
        # ЛР2 могла содержать INSERT с явными ID; синхронизируем обе последовательности.
        for table, column in [
            ("laboratory_synthesis_users", "laboratory_synthesis_user_id"),
            ("laboratory_syntheses", "laboratory_synthesis_id"),
        ]:
            model = LaboratorySynthesisUser if table.endswith("_users") else LaboratorySynthesis
            maximum = await session.scalar(select(func.max(getattr(model, column))))
            if maximum is not None:
                await session.execute(select(func.setval(
                    func.pg_get_serial_sequence(table, column), maximum, True,
                )))
        await session.commit()
    print("Демоданные и тестовые медиа готовы; существующие записи сохранены.")


if __name__ == "__main__":
    asyncio.run(main())
