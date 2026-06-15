from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from payments.entities.enums import Currency


@dataclass(frozen=True)
class CreatePaymentInput:
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    webhook_url: str
    idempotency_key: str
