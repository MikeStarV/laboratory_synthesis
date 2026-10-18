"""Фиксированный создатель ЛР3. Авторизация появится в ЛР4."""

from dataclasses import dataclass
from functools import lru_cache


LABORATORY_SYNTHESIS_CURRENT_USER_ID = 1


@dataclass(frozen=True)
class LaboratorySynthesisCurrentUser:
    laboratory_synthesis_user_id: int


@lru_cache(maxsize=1)
def get_laboratory_synthesis_current_user() -> LaboratorySynthesisCurrentUser:
    """Singleton: все запросы ЛР3 выполняются от пользователя 1."""
    return LaboratorySynthesisCurrentUser(
        laboratory_synthesis_user_id=LABORATORY_SYNTHESIS_CURRENT_USER_ID,
    )
