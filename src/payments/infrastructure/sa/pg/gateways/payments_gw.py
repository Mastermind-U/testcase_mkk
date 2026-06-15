from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payments.entities.entities import Payment


class SAPGPaymentGateway:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Payment | None:
        stmt = select(Payment).filter_by(idempotency_key=idempotency_key)
        return await self._session.scalar(stmt)

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return await self._session.get(Payment, payment_id)
