from typing import Protocol
from uuid import UUID

from payments.entities.entities import Payment


class SendWebhookGateway(Protocol):
    async def get_by_id(self, payment_id: UUID) -> Payment | None: ...
