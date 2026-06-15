from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from dci_template.application.commands.outbox_processor.gateway import (
    OutboxProcessorGateway,
)
from dci_template.application.commands.outbox_processor.interactor import (
    OutboxProcessorInteractor,
)
from dci_template.application.commands.outbox_processor.publisher import (
    OutboxPublisher,
)
from dci_template.application.transaction_manager import TransactionManager
from dci_template.entities.entities import OutboxEvent
from dci_template.entities.enums import OutboxStatus


async def test_outbox_processor_publishes_waiting() -> None:
    event = OutboxEvent(
        event_type="user.created",
        payload={"id": 1},
        retry_times=0,
        max_retries=2,
        status=OutboxStatus.PENDING,
    )

    gw = AsyncMock(spec=OutboxProcessorGateway)
    gw.get_waiting.return_value = [event]
    gw.delete_old.return_value = 0
    publisher = AsyncMock(spec=OutboxPublisher)
    tx = AsyncMock(spec=TransactionManager)
    interactor = OutboxProcessorInteractor(gw, publisher, tx)

    result = await interactor.execute()

    assert result.fetched == 1
    assert result.published == 1
    assert result.retried == 0
    assert result.dead_lettered == 0
    publisher.publish.assert_awaited_once_with(event)
    gw.update_sent_status.assert_awaited_once_with(event)
    tx.commit.assert_awaited()


async def test_outbox_processor_backoff_failed() -> None:
    event = OutboxEvent(
        event_type="user.created",
        payload={"id": 1},
        retry_times=0,
        max_retries=2,
        status=OutboxStatus.PENDING,
    )
    now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    event.get_now = lambda: now  # type: ignore[method-assign]
    event.jitter_factory = lambda base: timedelta(0)  # type: ignore[method-assign]  # noqa: ARG005

    gw = AsyncMock(spec=OutboxProcessorGateway)
    gw.get_waiting.return_value = [event]
    gw.delete_old.return_value = 0
    publisher = AsyncMock(spec=OutboxPublisher)
    publisher.publish.side_effect = RuntimeError("kafka is down")
    tx = AsyncMock(spec=TransactionManager)
    interactor = OutboxProcessorInteractor(gw, publisher, tx)

    result = await interactor.execute()

    assert result.fetched == 1
    assert result.published == 0
    assert result.retried == 1
    assert result.dead_lettered == 0
    assert event.status == OutboxStatus.FAILED
    assert event.retry_times == 1
    assert event.next_retry_at == now + timedelta(minutes=1)
    assert event.failure_reason == "kafka is down"
    tx.commit.assert_awaited()


async def test_outbox_processor_dead_lettered() -> None:
    event = OutboxEvent(
        event_type="user.created",
        payload={"id": 1},
        retry_times=1,
        max_retries=1,
    )
    now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    event.get_now = lambda: now  # type: ignore[method-assign]
    event.jitter_factory = lambda base: timedelta(0)  # type: ignore[method-assign]  # noqa: ARG005

    gw = AsyncMock(spec=OutboxProcessorGateway)
    gw.get_waiting.return_value = [event]
    gw.delete_old.return_value = 0
    publisher = AsyncMock(spec=OutboxPublisher)
    publisher.publish.side_effect = RuntimeError("kafka is down")
    tx = AsyncMock(spec=TransactionManager)
    interactor = OutboxProcessorInteractor(gw, publisher, tx)

    result = await interactor.execute()

    assert result.retried == 0
    assert result.dead_lettered == 1
    assert event.status == OutboxStatus.DEAD_LETTER
    assert event.next_retry_at is None
