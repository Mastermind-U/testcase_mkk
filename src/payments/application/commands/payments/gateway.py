from typing import Protocol

from payments.entities.entities import Payment


class PaymentCommandGateway(Protocol):
    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Payment | None: ...
