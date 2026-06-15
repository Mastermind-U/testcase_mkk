from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from payments.entities.entities import Payment
from payments.entities.enums import Currency, PaymentStatus


@dataclass(frozen=True)
class PaymentDTO:
    id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_entity(cls, payment: Payment) -> PaymentDTO:
        return cls(
            id=payment.id,
            amount=payment.amount.amount,
            currency=payment.amount.currency,
            description=payment.description,
            metadata=payment.metadata,
            status=payment.status,
            idempotency_key=payment.idempotency_key,
            webhook_url=payment.webhook_url,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )
