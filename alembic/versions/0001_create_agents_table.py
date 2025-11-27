from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("persona", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default="novice"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sandboxed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("mentor_id", sa.String(), sa.ForeignKey("agents.id")),
    )


def downgrade() -> None:
    op.drop_table("agents")

