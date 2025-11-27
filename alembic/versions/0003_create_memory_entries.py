from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from pgvector.sqlalchemy import Vector  # type: ignore
        op.create_table(
            "entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("tags", sa.ARRAY(sa.String()), nullable=True),
            sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("timestamp", sa.Float(), nullable=False),
            sa.Column("embedding", Vector(64)),
            sa.Column("search", sa.types.TSVECTOR),
        )
        op.create_index(
            "idx_entries_search", "entries", ["search"], postgresql_using="gin"
        )
    else:
        op.create_table(
            "entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("tags", sa.String(), nullable=True),
            sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("timestamp", sa.Float(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("entries")
