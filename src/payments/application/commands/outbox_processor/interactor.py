from __future__ import annotations

from structlog import get_logger

from payments.application.commands.outbox_processor.dto import (
    OutboxProcessorResult,
)
from payments.application.commands.outbox_processor.gateway import (
    OutboxProcessorGateway,
)
from payments.application.commands.outbox_processor.publisher import (
    OutboxPublisher,
)
from payments.application.transaction_manager import TransactionManager
from payments.entities.enums import OutboxStatus

_logger = get_logger(source="OutboxProcessorInteractor")


class OutboxProcessorInteractor:
    def __init__(
        self,
        gw: OutboxProcessorGateway,
        publisher: OutboxPublisher,
        transaction_manager: TransactionManager,
    ) -> None:
        self._gw = gw
        self._publisher = publisher
        self._tx = transaction_manager

    async def execute(self, limit: int = 100) -> OutboxProcessorResult:
        waiting = await self._gw.get_waiting(limit=limit)

        published = 0
        retried = 0
        dead_lettered = 0

        for event in waiting:
            try:
                await self._publisher.publish(event)
            except Exception as exc:
                event.mark_failed(str(exc))

                if event.status == OutboxStatus.FAILED:
                    retried += 1
                if event.status == OutboxStatus.DEAD_LETTER:
                    dead_lettered += 1

                await self._tx.commit()
                continue

            await self._gw.update_sent_status(event)
            await self._tx.commit()
            published += 1

        deleted_old = await self._gw.delete_old()
        await self._tx.commit()

        retval = OutboxProcessorResult(
            fetched=len(waiting),
            published=published,
            retried=retried,
            dead_lettered=dead_lettered,
            deleted_old=deleted_old,
        )
        if retval.is_not_mpty():
            _logger.info(retval)
        return retval
