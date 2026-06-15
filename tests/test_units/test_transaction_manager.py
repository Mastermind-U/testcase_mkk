from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from payments.entities.entities import BaseEntity
from payments.infrastructure.sa.pg.transaction_manager import (
    SAPGEntitySaver,
    SAPGTransactionManager,
)


async def test_transaction_manager_commit_calls_session_commit() -> None:
    session = AsyncMock(spec=AsyncSession)
    manager = SAPGTransactionManager(session)
    await manager.commit()
    session.commit.assert_awaited_once()


async def test_transaction_manager_rollback_calls_session_rollback() -> None:
    session = AsyncMock(spec=AsyncSession)
    manager = SAPGTransactionManager(session)
    await manager.rollback()
    session.rollback.assert_awaited_once()


async def test_entity_saver_add_one_calls_session_add() -> None:
    session = AsyncMock(spec=AsyncSession)
    saver = SAPGEntitySaver(session)
    entity = BaseEntity()

    saver.add_one(entity)

    session.add.assert_called_once_with(entity)


async def test_entity_saver_delete_calls_session_delete() -> None:
    session = AsyncMock(spec=AsyncSession)
    saver = SAPGEntitySaver(session)
    entity = BaseEntity()

    await saver.delete(entity)

    session.delete.assert_awaited_once_with(entity)
