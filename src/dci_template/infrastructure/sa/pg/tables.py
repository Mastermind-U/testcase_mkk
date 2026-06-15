from __future__ import annotations

from typing import TypeVar, cast

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import QueryableAttribute, registry

from dci_template.entities.entities import (
    OutboxEvent,
    OutboxStatus,
    TransactionalInbox,
)

T = TypeVar("T")


def q[T](value: T) -> QueryableAttribute[T]:
    return cast("QueryableAttribute[T]", value)


mapper_registry = registry()
metadata: MetaData = mapper_registry.metadata

transactional_inbox_t = Table(
    "transactional_inbox",
    metadata,
    Column(
        "correlation_id",
        PG_UUID(as_uuid=True),
        primary_key=True,
        key="event_id",
    ),
    Column("event_type", String, nullable=False),
    Column(
        "processed_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

outbox_t = Table(
    "outbox_events",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("event_type", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("sent_at", DateTime(timezone=True), nullable=True),
    Column("next_retry_at", DateTime(timezone=True), nullable=True),
    Column("failure_reason", Text, nullable=True),
    Column("last_error_at", DateTime(timezone=True), nullable=True),
    Column(
        "status",
        SAEnum(
            OutboxStatus,
            name="outbox_status",
        ),
        nullable=False,
        default=OutboxStatus.PENDING,
    ),
    Column(
        "retry_times",
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    ),
    Column(
        "max_retries",
        Integer,
        nullable=False,
        server_default=text("1"),
        default=1,
    ),
)

mapper_registry.map_imperatively(TransactionalInbox, transactional_inbox_t)
mapper_registry.map_imperatively(OutboxEvent, outbox_t)
