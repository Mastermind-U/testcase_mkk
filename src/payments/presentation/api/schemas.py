from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, TypeAdapter

from payments.application.common.payment_dto import PaymentDTO
from payments.entities.enums import Currency, PaymentStatus

webhook_url_adapter = TypeAdapter(AnyHttpUrl)


class StatusResponse(BaseModel):
    status: bool


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Currency
    description: str = Field(min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: AnyHttpUrl | None = None


class CreatePaymentResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime

    @classmethod
    def from_dto(cls, payment: PaymentDTO) -> CreatePaymentResponse:
        return cls(
            payment_id=payment.id,
            status=payment.status,
            created_at=payment.created_at,
        )


class PaymentResponse(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    idempotency_key: str
    webhook_url: AnyHttpUrl | None
    created_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_dto(cls, payment: PaymentDTO) -> PaymentResponse:
        return cls(
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            metadata=payment.metadata,
            status=payment.status,
            idempotency_key=payment.idempotency_key,
            webhook_url=webhook_url_adapter.validate_python(
                payment.webhook_url,
            )
            if payment.webhook_url is not None
            else None,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )
