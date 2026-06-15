from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.commands.outbox_processor.gateway import (
    OutboxProcessorGateway,
)
from payments.entities.entities import OutboxEvent
from payments.entities.enums import OutboxStatus
from payments.infrastructure.sa.pg.tables import q


class SAPGOutboxProcessorGateway(OutboxProcessorGateway):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_waiting(self, limit: int = 100) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        waiting_statuses = (OutboxStatus.PENDING, OutboxStatus.FAILED)
        stmt = (
            select(OutboxEvent)
            .where(q(OutboxEvent.sent_at).is_(None))
            .where(q(OutboxEvent.status).in_(waiting_statuses))
            .where(q(OutboxEvent.retry_times) <= OutboxEvent.max_retries)
            .where(
                q(OutboxEvent.next_retry_at).is_(None)
                | (q(OutboxEvent.next_retry_at) <= now),
            )
            .order_by(q(OutboxEvent.created_at).asc())  # type:ignore
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def update_sent_status(self, event: OutboxEvent) -> None:
        now = datetime.now(UTC)
        event.status = OutboxStatus.PUBLISHED
        event.sent_at = now
        event.next_retry_at = None
        event.failure_reason = None
        event.last_error_at = None

    async def delete_old(self) -> int:
        threshold = datetime.now(UTC) - timedelta(days=30)
        stmt = delete(OutboxEvent).where(
            q(OutboxEvent.sent_at).is_not(None),
            q(OutboxEvent.sent_at) < threshold,
        )
        result = await self._session.execute(stmt)
        return int(result.rowcount) or 0  # type: ignore
