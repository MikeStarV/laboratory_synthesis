"""Add media object keys and password hashes for laboratory work 3.

Revision ID: 51c47aa8c301
Revises: 038454f3eb69
"""

from alembic import op
import sqlalchemy as sa


revision = "51c47aa8c301"
down_revision = "038454f3eb69"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "laboratory_synthesis_users",
        sa.Column("laboratory_synthesis_user_password_hash", sa.String(256)),
    )
    op.add_column(
        "laboratory_syntheses",
        sa.Column("laboratory_synthesis_image_key", sa.String(255)),
    )
    op.add_column(
        "laboratory_syntheses",
        sa.Column("laboratory_synthesis_video_key", sa.String(255)),
    )


def downgrade() -> None:
    op.drop_column("laboratory_syntheses", "laboratory_synthesis_video_key")
    op.drop_column("laboratory_syntheses", "laboratory_synthesis_image_key")
    op.drop_column(
        "laboratory_synthesis_users", "laboratory_synthesis_user_password_hash",
    )
