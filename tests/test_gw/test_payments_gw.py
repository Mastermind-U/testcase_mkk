from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.entities.entities import Money, Payment
from payments.entities.enums import Currency
from payments.infrastructure.sa.pg.gateways.payments_gw import (
    SAPGPaymentGateway,
)


@pytest_asyncio.fixture
async def payments_gw(session: AsyncSession) -> SAPGPaymentGateway:
    return SAPGPaymentGateway(session)


def make_payment(idempotency_key: str = "key-1") -> Payment:
    return Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={"order_id": "42"},
        idempotency_key=idempotency_key,
        webhook_url="https://example.com/webhook",
    )


async def test_payment_gateway_gets_by_id(
    session: AsyncSession,
    payments_gw: SAPGPaymentGateway,
) -> None:
    payment = make_payment()
    session.add(payment)
    await session.flush()

    result = await payments_gw.get_by_id(payment.id)

    assert result is not None
    assert result.id == payment.id


async def test_payment_gateway_gets_by_idempotency_key(
    session: AsyncSession,
    payments_gw: SAPGPaymentGateway,
) -> None:
    payment = make_payment()
    session.add(payment)
    await session.flush()

    result = await payments_gw.get_by_idempotency_key("key-1")

    assert result is not None
    assert result.id == payment.id


async def test_payments_idempotency_key_is_unique(
    session: AsyncSession,
) -> None:
    session.add(make_payment())
    session.add(make_payment())

    with pytest.raises(IntegrityError):
        await session.flush()
