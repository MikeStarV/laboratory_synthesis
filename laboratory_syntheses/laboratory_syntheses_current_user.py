"""Сессии ЛР4: Redis хранит пользователя, браузер — случайный идентификатор."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyCookie
from redis.asyncio import Redis
from redis.exceptions import RedisError

from .laboratory_syntheses_config import laboratory_syntheses_settings as settings
from .laboratory_syntheses_database import get_laboratory_syntheses_database_session
from .laboratory_syntheses_database_models import LaboratorySynthesisUser

SessionCookie = APIKeyCookie(name="session_id", auto_error=False)


@dataclass(frozen=True)
class LaboratorySynthesisCurrentUser:
    laboratory_synthesis_user_id: int | None


async def get_laboratory_synthesis_redis():
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True,
                            socket_connect_timeout=2, socket_timeout=2)
    try:
        yield client
    finally:
        await client.aclose()


async def read_session(session_id, redis, session):
    if not session_id or len(session_id) > 128:
        return LaboratorySynthesisCurrentUser(None)
    try:
        value = await redis.get(f"session:{session_id}")
    except RedisError as error:
        raise HTTPException(503, "Хранилище сессий временно недоступно") from error
    try:
        user_id = int(value)
    except (TypeError, ValueError):
        return LaboratorySynthesisCurrentUser(None)
    user = await session.get(LaboratorySynthesisUser, user_id)
    return LaboratorySynthesisCurrentUser(user_id if user is not None else None)


async def get_optional_laboratory_synthesis_user(
    request: Request,
    redis=Depends(get_laboratory_synthesis_redis),
    session=Depends(get_laboratory_syntheses_database_session),
):
    return await read_session(request.cookies.get("session_id"), redis, session)


async def get_laboratory_synthesis_current_user(
    session_id: Annotated[str | None, Security(SessionCookie)],
    redis=Depends(get_laboratory_synthesis_redis),
    session=Depends(get_laboratory_syntheses_database_session),
):
    user = await read_session(session_id, redis, session)
    if user.laboratory_synthesis_user_id is None:
        raise HTTPException(401, "Требуется вход в систему")
    return user
