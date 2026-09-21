"""Единственная модель услуги для ЛР1; массы относятся к будущей заявке."""
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class LaboratorySynthesisStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DELETED = "deleted"


class LaboratorySynthesis(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    laboratory_synthesis_id: int = Field(gt=0)
    laboratory_synthesis_name: str = Field(min_length=1, max_length=120)
    laboratory_synthesis_description: str = Field(min_length=1)
    laboratory_synthesis_duration_minutes: int = Field(gt=0, le=240)
    laboratory_synthesis_temperature_celsius: float = Field(ge=-273.15)
    laboratory_synthesis_image_key: str
    laboratory_synthesis_video_key: str
    laboratory_synthesis_status: LaboratorySynthesisStatus
    laboratory_synthesis_liked_by_user_ids: list[int] = Field(default_factory=list)
