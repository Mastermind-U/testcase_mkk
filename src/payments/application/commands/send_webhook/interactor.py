from uuid import UUID

from payments.application.commands.send_webhook.gateway import (
    SendWebhookGateway,
)
from payments.application.commands.send_webhook.services import WebhookSender
from payments.application.common.payment_dto import PaymentDTO
from payments.entities.exceptions import ObjectNotFoundError


class SendWebhookInteractor:
    def __init__(
        self,
        gw: SendWebhookGateway,
        webhook_sender: WebhookSender,
    ) -> None:
        self._gw = gw
        self._webhook_sender = webhook_sender

    async def execute(self, payment_id: UUID) -> None:
        payment = await self._gw.get_by_id(payment_id)
        if payment is None:
            raise ObjectNotFoundError

        if not payment.webhook_url:
            return

        await self._webhook_sender.send(PaymentDTO.from_entity(payment))
