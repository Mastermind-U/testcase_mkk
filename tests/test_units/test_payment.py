from decimal import Decimal

import pytest

from payments.entities.entities import Money, OutboxEvent, Payment
from payments.entities.enums import Currency, OutboxStatus, PaymentStatus
from payments.entities.exceptions import ValidationError


def test_payment_mark_succeeded_sets_status_and_processed_at() -> None:
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
    )

    payment.mark_succeeded()

    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.processed_at is not None


def test_payment_mark_failed_sets_status_and_processed_at() -> None:
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
    )

    payment.mark_failed()

    assert payment.status == PaymentStatus.FAILED
    assert payment.processed_at is not None


def test_outbox_event_defaults_to_three_retries() -> None:
    event = OutboxEvent(event_type="payments.new", payload={})

    assert event.status == OutboxStatus.PENDING
    assert event.max_retries == 3


def test_money_rejects_cross_currency_operations() -> None:
    rubles = Money(Decimal("100.00"), Currency.RUB)
    dollars = Money(Decimal("100.00"), Currency.USD)

    with pytest.raises(ValidationError, match="same currency"):
        rubles + dollars  # pyright: ignore[reportUnusedExpression]


def test_money_rejects_negative_amount() -> None:
    with pytest.raises(ValidationError, match="negative"):
        Money(Decimal("-0.01"))


def test_money_quantizes_amount() -> None:
    assert Money(Decimal("10.005")).amount == Decimal("10.01")


def test_money_zero_uses_requested_currency() -> None:
    assert Money.zero(Currency.USD) == Money(Decimal("0.00"), Currency.USD)


def test_money_converts_to_float_int_cents_and_str() -> None:
    amount = Money(Decimal("10.50"))

    assert amount.as_float() == 10.5
    assert amount.as_int_cents() == 1050
    assert amount.as_str() == "10.50"
