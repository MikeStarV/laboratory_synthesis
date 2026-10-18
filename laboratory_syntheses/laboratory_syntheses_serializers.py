"""Входные DTO и публичные JSON-сериализаторы ЛР3."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from .laboratory_syntheses_database_models import LaboratorySynthesisStatus


class LaboratorySynthesisInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LaboratorySynthesisDraftInput(LaboratorySynthesisInput):
    laboratory_synthesis_name: str = Field(min_length=1, max_length=120)
    laboratory_synthesis_description: str = Field(min_length=1, max_length=5000)
    laboratory_synthesis_duration_minutes: int = Field(ge=1, le=90)
    laboratory_synthesis_temperature_celsius: float = Field(
        ge=-273.15, allow_inf_nan=False,
    )


class LaboratorySynthesisPublicationInput(LaboratorySynthesisInput):
    """Публикация не принимает статус, автора, даты или другие поля."""


class LaboratorySynthesisLikeInput(LaboratorySynthesisInput):
    laboratory_synthesis_liked: Annotated[int, Field(strict=True, ge=0, le=1)]


class LaboratorySynthesisRegistrationInput(LaboratorySynthesisInput):
    laboratory_synthesis_user_name: str = Field(min_length=3, max_length=100)
    laboratory_synthesis_user_password: SecretStr = Field(
        min_length=8, max_length=128,
    )

    @field_validator("laboratory_synthesis_user_password")
    @classmethod
    def laboratory_synthesis_password_is_not_blank(cls, value: SecretStr):
        if not value.get_secret_value().strip():
            raise ValueError("Пароль не должен состоять только из пробелов")
        return value


class LaboratorySynthesisUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    laboratory_synthesis_user_id: int
    laboratory_synthesis_user_name: str


class LaboratorySynthesisResponse(BaseModel):
    laboratory_synthesis_id: int
    laboratory_synthesis_name: str
    laboratory_synthesis_description: str | None
    laboratory_synthesis_duration_minutes: int | None
    laboratory_synthesis_temperature_celsius: float | None
    laboratory_synthesis_status: LaboratorySynthesisStatus
    laboratory_synthesis_image_key: str | None
    laboratory_synthesis_video_key: str | None
    laboratory_synthesis_image_url: str | None
    laboratory_synthesis_video_url: str | None
    laboratory_synthesis_created_at: datetime
    laboratory_synthesis_formed_at: datetime | None
    laboratory_synthesis_creator: LaboratorySynthesisUserResponse
    laboratory_synthesis_is_creator: Literal[0, 1]
    laboratory_synthesis_liked: Literal[0, 1]
    laboratory_synthesis_likes_count: int
