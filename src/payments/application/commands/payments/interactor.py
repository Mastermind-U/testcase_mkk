from payments.application.commands.payments.dto import CreatePaymentInput
from payments.application.commands.payments.gateway import (
    PaymentCommandGateway,
)
from payments.application.common.payment_dto import PaymentDTO
from payments.application.transaction_manager import (
    EntitySaver,
    TransactionManager,
)
from payments.entities.entities import OutboxEvent, Payment
from payments.entities.value_objects import Money


class CreatePaymentInteractor:
    def __init__(
        self,
        gw: PaymentCommandGateway,
        entity_saver: EntitySaver,
        transaction_manager: TransactionManager,
    ) -> None:
        self._gw = gw
        self._entity_saver = entity_saver
        self._tx = transaction_manager

    async def execute(self, data: CreatePaymentInput) -> PaymentDTO:
        existing = await self._gw.get_by_idempotency_key(
            data.idempotency_key,
        )
        if existing is not None:
            return PaymentDTO.from_entity(existing)

        payment = Payment(
            amount=Money(data.amount, data.currency),
            description=data.description,
            metadata=data.metadata,
            idempotency_key=data.idempotency_key,
            webhook_url=data.webhook_url,
        )
        outbox_event = OutboxEvent(
            event_type="payments.new",
            payload={"payment_id": str(payment.id)},
        )
        self._entity_saver.add_one(payment)
        self._entity_saver.add_one(outbox_event)
        await self._tx.commit()
        return PaymentDTO.from_entity(payment)
