from sqlalchemy.ext.asyncio import AsyncSession

from payments.entities.entities import BaseEntity


class SAPGTransactionManager:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


class SAPGEntitySaver:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_one(self, entity: BaseEntity) -> None:
        self._session.add(entity)

    async def delete(self, entity: BaseEntity) -> None:
        await self._session.delete(entity)
