"""init migration.

Revision ID: 609f2b15f56c
Revises:
Create Date: 2026-04-10 20:26:43.861059

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from dishka import AsyncContainer
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "609f2b15f56c"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(container: AsyncContainer) -> None:  # noqa: ARG001
    """Upgrade schema."""
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PUBLISHED",
                "FAILED",
                "DEAD_LETTER",
                name="outbox_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "retry_times",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "max_retries",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transactional_inbox",
        sa.Column("correlation_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("correlation_id"),
    )
    # ### end Alembic commands ###


def downgrade(container: AsyncContainer) -> None:  # noqa: ARG001
    """Downgrade schema."""
    op.drop_table("transactional_inbox")
    op.drop_table("outbox_events")
    op.execute("DROP TYPE IF EXISTS outbox_status")
