from datetime import UTC, datetime, timedelta

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payments.entities.entities import OutboxEvent
from payments.entities.enums import OutboxStatus
from payments.infrastructure.sa.pg.gateways.outbox_processor_gw import (
    SAPGOutboxProcessorGateway,
)


@pytest_asyncio.fixture
async def outbox_gw(session: AsyncSession) -> SAPGOutboxProcessorGateway:
    return SAPGOutboxProcessorGateway(session)


async def test_outbox_gateway_get_waiting_returns_only_ready_events(
    session: AsyncSession,
    outbox_gw: SAPGOutboxProcessorGateway,
) -> None:
    now = datetime.now(UTC)

    ready_first = OutboxEvent(event_type="user.created", payload={"id": 1})

    ready_second = OutboxEvent(
        event_type="user.created",
        payload={"id": 2},
        status=OutboxStatus.FAILED,
    )
    ready_second.next_retry_at = now - timedelta(minutes=1)

    sent = OutboxEvent(
        event_type="user.created",
        payload={"id": 3},
        status=OutboxStatus.PUBLISHED,
    )
    sent.sent_at = now - timedelta(minutes=7)

    waiting_retry = OutboxEvent(
        event_type="user.created",
        payload={"id": 4},
        status=OutboxStatus.FAILED,
    )
    waiting_retry.next_retry_at = now + timedelta(minutes=1)

    exhausted = OutboxEvent(
        event_type="user.created",
        payload={"id": 5},
        status=OutboxStatus.FAILED,
        retry_times=2,
        max_retries=1,
    )

    session.add_all(
        [
            ready_first,
            ready_second,
            sent,
            waiting_retry,
            exhausted,
        ],
    )
    await session.flush()

    rows = await outbox_gw.get_waiting(limit=10)

    assert {row.id for row in rows} == {ready_first.id, ready_second.id}


async def test_outbox_gateway_update_sent_status_persists_changes(
    session: AsyncSession,
    outbox_gw: SAPGOutboxProcessorGateway,
) -> None:
    event = OutboxEvent(
        event_type="user.created",
        payload={"id": 1},
        status=OutboxStatus.FAILED,
    )
    event.failure_reason = "temporary error"
    event.last_error_at = datetime.now(UTC) - timedelta(minutes=3)
    event.next_retry_at = datetime.now(UTC) + timedelta(minutes=1)
    session.add(event)
    await session.flush()
    event_id = event.id

    await outbox_gw.update_sent_status(event)
    await session.flush()
    session.expire_all()

    reloaded = await session.get(OutboxEvent, event_id)

    assert reloaded is not None
    assert reloaded.status == OutboxStatus.PUBLISHED
    assert reloaded.sent_at is not None
    assert reloaded.next_retry_at is None
    assert reloaded.failure_reason is None
    assert reloaded.last_error_at is None


async def test_outbox_gateway_delete_old_removes_only_old_sent(
    session: AsyncSession,
    outbox_gw: SAPGOutboxProcessorGateway,
) -> None:
    now = datetime.now(UTC)

    old_sent = OutboxEvent(
        event_type="user.created",
        payload={"id": 1},
        status=OutboxStatus.PUBLISHED,
    )
    old_sent.sent_at = now - timedelta(days=31)

    recent_sent = OutboxEvent(
        event_type="user.created",
        payload={"id": 2},
        status=OutboxStatus.PUBLISHED,
    )
    recent_sent.sent_at = now - timedelta(days=5)

    pending = OutboxEvent(event_type="user.created", payload={"id": 3})

    session.add_all([old_sent, recent_sent, pending])
    await session.flush()

    deleted = await outbox_gw.delete_old()
    await session.flush()
    session.expire_all()

    remaining = await session.scalars(select(OutboxEvent))
    remaining_ids = {event.id for event in remaining}

    assert deleted == 1
    assert old_sent.id not in remaining_ids
    assert recent_sent.id in remaining_ids
    assert pending.id in remaining_ids
