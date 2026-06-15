from __future__ import annotations

from typing import TypeVar, cast

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import QueryableAttribute, composite, registry

from payments.entities.entities import (
    Money,
    OutboxEvent,
    OutboxStatus,
    Payment,
    TransactionalInbox,
)
from payments.entities.enums import Currency, PaymentStatus

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

payments_t = Table(
    "payments",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("amount", Numeric(precision=18, scale=2), nullable=False),
    Column(
        "currency",
        SAEnum(Currency, name="payment_currency"),
        nullable=False,
    ),
    Column("description", Text, nullable=False),
    Column("metadata", JSON, nullable=False),
    Column("idempotency_key", String, nullable=False),
    Column("webhook_url", Text, nullable=True),
    Column(
        "status",
        SAEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("processed_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
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
        server_default=text("3"),
        default=3,
    ),
)

mapper_registry.map_imperatively(TransactionalInbox, transactional_inbox_t)
mapper_registry.map_imperatively(
    Payment,
    payments_t,
    properties={
        "_amount_amount": payments_t.c.amount,
        "_amount_currency": payments_t.c.currency,
        "amount": composite(
            Money,
            "_amount_amount",
            "_amount_currency",
        ),
    },
)
mapper_registry.map_imperatively(OutboxEvent, outbox_t)
