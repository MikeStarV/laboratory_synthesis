import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .laboratory_syntheses_database import (
    LaboratorySynthesesDatabaseModel,
)


class LaboratorySynthesisStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DELETED = "deleted"


class LaboratorySynthesisUser(LaboratorySynthesesDatabaseModel):
    __tablename__ = "laboratory_synthesis_users"

    laboratory_synthesis_user_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    laboratory_synthesis_user_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    laboratory_synthesis_user_password_hash: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )

    laboratory_syntheses: Mapped[list["LaboratorySynthesis"]] = relationship(
        back_populates="laboratory_synthesis_creator",
    )

    laboratory_synthesis_likes: Mapped[list["LaboratorySynthesisLike"]] = (
        relationship(
            back_populates="laboratory_synthesis_user",
        )
    )


class LaboratorySynthesis(LaboratorySynthesesDatabaseModel):
    __tablename__ = "laboratory_syntheses"

    laboratory_synthesis_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    laboratory_synthesis_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    laboratory_synthesis_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    laboratory_synthesis_status: Mapped[LaboratorySynthesisStatus] = (
        mapped_column(
            Enum(
                LaboratorySynthesisStatus,
                name="laboratory_synthesis_status",
                values_callable=lambda statuses: [
                    status.value for status in statuses
                ],
            ),
            nullable=False,
            default=LaboratorySynthesisStatus.DRAFT,
        )
    )

    laboratory_synthesis_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    laboratory_synthesis_video_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    laboratory_synthesis_image_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    laboratory_synthesis_video_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    laboratory_synthesis_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    laboratory_synthesis_temperature_celsius: Mapped[float | None] = (
        mapped_column(
            Float,
            nullable=True,
        )
    )

    laboratory_synthesis_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    laboratory_synthesis_formed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    laboratory_synthesis_creator_id: Mapped[int] = mapped_column(
        ForeignKey(
            "laboratory_synthesis_users.laboratory_synthesis_user_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    laboratory_synthesis_creator: Mapped[LaboratorySynthesisUser] = relationship(
        back_populates="laboratory_syntheses",
    )

    laboratory_synthesis_likes: Mapped[list["LaboratorySynthesisLike"]] = (
        relationship(
            back_populates="laboratory_synthesis",
        )
    )

    __table_args__ = (
        Index(
            "uq_laboratory_synthesis_draft_per_user",
            "laboratory_synthesis_creator_id",
            unique=True,
            postgresql_where=text(
                "laboratory_synthesis_status = 'draft'"
            ),
            sqlite_where=text(
                "laboratory_synthesis_status = 'draft'"
            ),
        ),
    )


class LaboratorySynthesisLike(LaboratorySynthesesDatabaseModel):
    __tablename__ = "laboratory_synthesis_likes"

    laboratory_synthesis_like_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    laboratory_synthesis_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "laboratory_synthesis_users.laboratory_synthesis_user_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    laboratory_synthesis_id: Mapped[int] = mapped_column(
        ForeignKey(
            "laboratory_syntheses.laboratory_synthesis_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    laboratory_synthesis_user: Mapped[LaboratorySynthesisUser] = relationship(
        back_populates="laboratory_synthesis_likes",
    )

    laboratory_synthesis: Mapped[LaboratorySynthesis] = relationship(
        back_populates="laboratory_synthesis_likes",
    )

    __table_args__ = (
        UniqueConstraint(
            "laboratory_synthesis_user_id",
            "laboratory_synthesis_id",
            name="uq_laboratory_synthesis_like",
        ),
    )
