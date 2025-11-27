from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("mission", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("ts", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("missions")
