from uuid import UUID

from payments.application.commands.send_webhook.gateway import (
    SendWebhookGateway,
)
from payments.application.commands.send_webhook.services import WebhookSender
from payments.application.common.payment_dto import PaymentDTO
from payments.application.transaction_manager import (
    EntitySaver,
    TransactionManager,
)
from payments.entities.entities import OutboxEvent
from payments.entities.exceptions import ObjectNotFoundError

WEBHOOK_EVENT_TYPE = "payments.webhook"


class SendWebhookInteractor:
    def __init__(
        self,
        gw: SendWebhookGateway,
        webhook_sender: WebhookSender,
        entity_saver: EntitySaver,
        transaction_manager: TransactionManager,
    ) -> None:
        self._gw = gw
        self._webhook_sender = webhook_sender
        self._entity_saver = entity_saver
        self._tx = transaction_manager

    async def execute(
        self,
        payment_id: UUID,
        retry_times: int = 0,
        max_retries: int = 3,
    ) -> None:
        payment = await self._gw.get_by_id(payment_id)
        if payment is None:
            raise ObjectNotFoundError

        if not payment.webhook_url:
            return

        try:
            await self._webhook_sender.send(PaymentDTO.from_entity(payment))
        except Exception as exc:
            retry_event = OutboxEvent(
                event_type=WEBHOOK_EVENT_TYPE,
                payload={"payment_id": str(payment_id)},
                retry_times=retry_times,
                max_retries=max_retries,
            )
            retry_event.mark_failed(str(exc))
            retry_event.payload["retry_times"] = retry_event.retry_times
            retry_event.payload["max_retries"] = retry_event.max_retries
            self._entity_saver.add_one(retry_event)
            await self._tx.commit()
            return

        await self._tx.commit()
