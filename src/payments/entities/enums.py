from enum import IntEnum, StrEnum


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OutboxStatus(IntEnum):
    PENDING = 1
    PUBLISHED = 2
    FAILED = 3
    DEAD_LETTER = 4
