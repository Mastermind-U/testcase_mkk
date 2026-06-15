from uuid import UUID

from payments.application.commands.process_payment.gateway import (
    PaymentProcessorGateway,
)
from payments.application.commands.process_payment.services import (
    PaymentGatewayEmulator,
)
from payments.application.common.payment_dto import PaymentDTO
from payments.application.transaction_manager import (
    EntitySaver,
    TransactionManager,
)
from payments.entities.entities import OutboxEvent
from payments.entities.enums import PaymentStatus
from payments.entities.exceptions import ObjectNotFoundError


class ProcessPaymentInteractor:
    def __init__(
        self,
        gw: PaymentProcessorGateway,
        payment_gateway: PaymentGatewayEmulator,
        entity_saver: EntitySaver,
        transaction_manager: TransactionManager,
    ) -> None:
        self._gw = gw
        self._payment_gateway = payment_gateway
        self._entity_saver = entity_saver
        self._tx = transaction_manager

    async def execute(self, payment_id: UUID) -> PaymentDTO:
        payment = await self._gw.get_by_id(payment_id)
        if payment is None:
            raise ObjectNotFoundError

        if payment.status != PaymentStatus.PENDING:
            return PaymentDTO.from_entity(payment)

        is_successful = await self._payment_gateway.process()
        if is_successful:
            payment.mark_succeeded()
        else:
            payment.mark_failed()

        result = PaymentDTO.from_entity(payment)
        if payment.webhook_url:
            self._entity_saver.add_one(
                OutboxEvent(
                    event_type="payments.webhook",
                    payload={"payment_id": str(payment.id)},
                ),
            )

        await self._tx.commit()
        return result
