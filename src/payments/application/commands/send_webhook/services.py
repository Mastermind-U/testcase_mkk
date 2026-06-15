from typing import Protocol

from payments.application.common.payment_dto import PaymentDTO


class WebhookSender(Protocol):
    async def send(self, payment: PaymentDTO) -> None: ...
