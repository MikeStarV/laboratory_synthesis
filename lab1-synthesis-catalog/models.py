from enum import Enum
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime


class SynthesisStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Synthesis(BaseModel):
    id: int
    name: str
    reagentName: str
    productName: str
    molarMassReagent: float
    molarMassProduct: float
    stoichiometricCoefficient: float
    reagentMass: float
    referenceYieldPercent: float          # эталонный % выхода по методике (справочное поле)
    description: str
    imageKey: str
    videoKey: str
    status: SynthesisStatus
    likedByUserIds: List[int] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
