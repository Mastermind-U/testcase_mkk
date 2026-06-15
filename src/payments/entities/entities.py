import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from random import uniform
from typing import Any

from .constants import OUTBOX_BACKOFF_JITTER_RATIO, OUTBOX_BACKOFF_MAX_MINUTES
from .enums import OutboxStatus, PaymentStatus
from .value_objects import Money


class BaseEntity: ...


@dataclass
class Payment(BaseEntity):
    amount: Money
    description: str
    metadata: dict[str, Any]
    idempotency_key: str
    webhook_url: str
    id: uuid.UUID = field(init=False, default_factory=uuid.uuid4)
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None

    def mark_succeeded(self) -> None:
        self.status = PaymentStatus.SUCCEEDED
        self.processed_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        self.status = PaymentStatus.FAILED
        self.processed_at = datetime.now(UTC)


@dataclass
class TransactionalInbox(BaseEntity):
    event_id: uuid.UUID
    event_type: str
    processed_at: datetime = field(
        init=False,
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass
class OutboxEvent(BaseEntity):
    id: uuid.UUID = field(init=False, default_factory=uuid.uuid4)
    event_type: str
    payload: dict[Any, Any]
    created_at: datetime = field(init=False)
    sent_at: datetime | None = None
    next_retry_at: datetime | None = None
    failure_reason: str | None = None
    last_error_at: datetime | None = None
    status: OutboxStatus = OutboxStatus.PENDING
    retry_times: int = 0
    max_retries: int = 3

    def get_now(self) -> datetime:
        return datetime.now(UTC)

    def jitter_factory(self, base: timedelta) -> timedelta:
        """Return a random jitter capped by the configured ratio."""
        jitter_seconds = uniform(
            0,
            base.total_seconds() * OUTBOX_BACKOFF_JITTER_RATIO,
        )
        return timedelta(seconds=jitter_seconds)

    def mark_failed(self, reason: str) -> None:
        """Record a publish failure and schedule the next retry if needed."""
        now = self.get_now()
        self.retry_times += 1
        self.last_error_at = now
        self.failure_reason = reason

        if self.retry_times >= self.max_retries:
            self.status = OutboxStatus.DEAD_LETTER
            self.next_retry_at = None
            return

        self.status = OutboxStatus.FAILED
        self.next_retry_at = now + self.next_retry_delay()

    @staticmethod
    def _backoff_delay(retry_times: int) -> timedelta:
        minutes = min(
            OUTBOX_BACKOFF_MAX_MINUTES,
            2 ** max(retry_times - 1, 0),
        )
        return timedelta(minutes=minutes)

    def next_retry_delay(self) -> timedelta:
        """Return the backoff delay including jitter."""
        base = self._backoff_delay(self.retry_times)
        return base + self.jitter_factory(base)
