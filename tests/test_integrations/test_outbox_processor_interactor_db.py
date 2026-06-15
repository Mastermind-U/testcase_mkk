from typing import cast
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

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
from dci_template.infrastructure.sa.pg.gateways.outbox_processor_gw import (
    SAPGOutboxProcessorGateway,
)
from dci_template.infrastructure.sa.pg.transaction_manager import (
    SAPGTransactionManager,
)


async def test_outbox_processor_marks_event_as_published(
    session: AsyncSession,
) -> None:
    event = OutboxEvent(event_type="user.created", payload={"id": 1})
    session.add(event)
    await session.flush()
    event_id = event.id

    gw: OutboxProcessorGateway = SAPGOutboxProcessorGateway(session)
    publisher_mock = AsyncMock(spec=OutboxPublisher)
    publisher = cast("OutboxPublisher", publisher_mock)
    tx: TransactionManager = SAPGTransactionManager(session)
    interactor = OutboxProcessorInteractor(gw, publisher, tx)

    await interactor.execute()

    session.expire_all()
    reloaded = await session.get(OutboxEvent, event_id)

    assert reloaded is not None
    assert reloaded.status == OutboxStatus.PUBLISHED
    assert reloaded.sent_at is not None
    publisher_mock.publish.assert_awaited_once()
