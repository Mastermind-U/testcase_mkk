from uuid import UUID

from payments.application.common.payment_dto import PaymentDTO
from payments.application.queries.payments.gateway import PaymentReadGateway
from payments.entities.exceptions import ObjectNotFoundError


class ReadPaymentInteractor:
    def __init__(self, gw: PaymentReadGateway) -> None:
        self._gw = gw

    async def execute(self, payment_id: UUID) -> PaymentDTO:
        payment = await self._gw.get_by_id(payment_id)
        if payment is None:
            raise ObjectNotFoundError
        return PaymentDTO.from_entity(payment)
