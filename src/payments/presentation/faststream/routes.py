from uuid import UUID

from dishka_faststream import FromDishka
from faststream.middlewares import AckPolicy
from faststream.rabbit import RabbitRouter
from pydantic import BaseModel

from payments.application.commands.process_payment import (
    ProcessPaymentInteractor,
)
from payments.application.commands.send_webhook import SendWebhookInteractor
from payments.presentation.faststream.rabbit import (
    payments_exchange,
    payments_new_queue,
    payments_webhook_queue,
)

router = RabbitRouter()


class PaymentNewMessage(BaseModel):
    payment_id: UUID


@router.subscriber(
    payments_new_queue,
    payments_exchange,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def process_payment(
    message: PaymentNewMessage,
    interactor: FromDishka[ProcessPaymentInteractor],
) -> None:
    await interactor.execute(message.payment_id)


@router.subscriber(
    payments_webhook_queue,
    payments_exchange,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def send_payment_webhook(
    message: PaymentNewMessage,
    interactor: FromDishka[SendWebhookInteractor],
) -> None:
    await interactor.execute(message.payment_id)
