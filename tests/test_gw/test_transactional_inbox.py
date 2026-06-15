import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from payments.entities.entities import TransactionalInbox
from payments.infrastructure.sa.pg.tables import transactional_inbox_t
from payments.infrastructure.sa.pg.transaction_manager import SAPGEntitySaver


@pytest_asyncio.fixture(scope="session", autouse=True)
async def transactional_inbox_table(
    engine: AsyncEngine,
) -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(
            transactional_inbox_t.create,
            checkfirst=True,
        )
    yield


async def test_entity_saver_persists_transactional_inbox(
    session: AsyncSession,
) -> None:
    event_id = uuid.uuid4()
    inbox_event = TransactionalInbox(
        event_id=event_id,
        event_type="user.created",
    )
    saver = SAPGEntitySaver(session)

    saver.add_one(inbox_event)
    await session.flush()
    session.expire_all()

    reloaded = await session.get(TransactionalInbox, event_id)

    assert reloaded is not None
    assert reloaded.event_id == event_id
    assert reloaded.event_type == "user.created"
    assert reloaded.processed_at is not None
