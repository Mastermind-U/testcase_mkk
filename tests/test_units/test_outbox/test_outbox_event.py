from datetime import UTC, datetime, timedelta

from payments.entities.entities import OutboxEvent
from payments.entities.enums import OutboxStatus


def test_outbox_event_mark_failed_sets_retry_backoff() -> None:
    event = OutboxEvent(event_type="user.created", payload={"id": 1})
    now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    event.get_now = lambda: now  # type: ignore[method-assign]
    event.jitter_factory = lambda base: timedelta(0)  # type: ignore[method-assign]  # noqa: ARG005

    event.mark_failed("rabbitmq is down")

    assert event.status == OutboxStatus.FAILED
    assert event.retry_times == 1
    assert event.failure_reason == "rabbitmq is down"
    assert event.last_error_at == now
    assert event.next_retry_at == now + timedelta(minutes=1)


def test_outbox_event_mark_failed_dead_letters_after_limit() -> None:
    event = OutboxEvent(event_type="user.created", payload={"id": 1})
    event.max_retries = 1
    now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    event.get_now = lambda: now  # type: ignore[method-assign]
    event.jitter_factory = lambda base: timedelta(0)  # type: ignore[method-assign]  # noqa: ARG005

    event.mark_failed("rabbitmq is down")

    assert event.status == OutboxStatus.DEAD_LETTER
    assert event.retry_times == 1
    assert event.next_retry_at is None


def test_outbox_event_defaults_to_three_total_attempts() -> None:
    event = OutboxEvent(event_type="user.created", payload={"id": 1})
    now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    event.get_now = lambda: now  # type: ignore[method-assign]
    event.jitter_factory = lambda base: timedelta(0)  # type: ignore[method-assign]  # noqa: ARG005

    event.mark_failed("rabbitmq is down")
    event.mark_failed("rabbitmq is down")
    event.mark_failed("rabbitmq is down")

    assert event.retry_times == 3
    assert event.status == OutboxStatus.DEAD_LETTER
    assert event.next_retry_at is None
