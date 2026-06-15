from decimal import Decimal

from payments.entities.enums import Currency

OUTBOX_BACKOFF_MAX_MINUTES = 60
OUTBOX_BACKOFF_JITTER_RATIO = 0.5

CURRENCY_SCALE = {
    Currency.RUB: Decimal("0.01"),
    Currency.USD: Decimal("0.01"),
    Currency.EUR: Decimal("0.01"),
}
