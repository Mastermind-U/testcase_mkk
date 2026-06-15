from decimal import Decimal
from typing import Any

import httpx

from payments.application.commands.send_webhook.services import WebhookSender
from payments.application.common.payment_dto import PaymentDTO


class HTTPXWebhookSender(WebhookSender):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def send(self, payment: PaymentDTO) -> None:
        if payment.webhook_url is None:
            return

        response = await self._client.post(
            payment.webhook_url,
            json=self._to_payload(payment),
        )
        response.raise_for_status()

    @staticmethod
    def _to_payload(payment: PaymentDTO) -> dict[str, Any]:
        return {
            "payment_id": str(payment.id),
            "status": payment.status.name.lower(),
            "amount": str(Decimal(payment.amount)),
            "currency": payment.currency.name,
            "description": payment.description,
            "metadata": payment.metadata,
            "created_at": payment.created_at.isoformat(),
            "processed_at": payment.processed_at.isoformat()
            if payment.processed_at is not None
            else None,
        }
