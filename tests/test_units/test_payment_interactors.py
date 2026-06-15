from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from payments.application.commands.payments import (
    CreatePaymentInput,
    CreatePaymentInteractor,
)
from payments.application.commands.process_payment import (
    ProcessPaymentInteractor,
)
from payments.application.commands.send_webhook import SendWebhookInteractor
from payments.application.common.payment_dto import PaymentDTO
from payments.application.queries.payments import ReadPaymentInteractor
from payments.entities.entities import BaseEntity, Money, OutboxEvent, Payment
from payments.entities.enums import Currency, PaymentStatus
from payments.entities.exceptions import ObjectNotFoundError


class PaymentGatewayFake:
    def __init__(self, payment: Payment | None = None) -> None:
        self.payment = payment

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Payment | None:
        if self.payment and self.payment.idempotency_key == idempotency_key:
            return self.payment
        return None

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        if self.payment and self.payment.id == payment_id:
            return self.payment
        return None


class EntitySaverFake:
    def __init__(self) -> None:
        self.saved: list[object] = []

    def add_one(self, entity: BaseEntity) -> None:
        self.saved.append(entity)

    async def delete(self, entity: BaseEntity) -> None:
        self.saved.remove(entity)


class TransactionManagerFake:
    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1


class PaymentGatewayEmulatorFake:
    def __init__(self, result: bool) -> None:
        self.result = result

    async def process(self) -> bool:
        return self.result


class WebhookSenderFake:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.sent: list[object] = []

    async def send(self, payment: PaymentDTO) -> None:
        if self.should_fail:
            raise RuntimeError("webhook is down")
        self.sent.append(payment)


def create_input() -> CreatePaymentInput:
    return CreatePaymentInput(
        amount=Decimal("10.00"),
        currency=Currency.RUB,
        description="Invoice",
        metadata={"order_id": "42"},
        webhook_url="https://example.com/webhook",
        idempotency_key="key-1",
    )


async def test_create_payment_creates_payment_and_outbox() -> None:
    saver = EntitySaverFake()
    tx = TransactionManagerFake()
    interactor = CreatePaymentInteractor(
        PaymentGatewayFake(),
        saver,
        tx,
    )

    result = await interactor.execute(create_input())

    assert result.status == PaymentStatus.PENDING
    assert tx.committed == 1
    assert len(saver.saved) == 2
    assert isinstance(saver.saved[0], Payment)
    assert isinstance(saver.saved[1], OutboxEvent)
    assert saver.saved[1].event_type == "payments.new"
    assert saver.saved[1].payload == {"payment_id": str(result.id)}


async def test_create_payment_returns_existing_for_duplicate_key() -> None:
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
    )
    saver = EntitySaverFake()
    tx = TransactionManagerFake()
    interactor = CreatePaymentInteractor(
        PaymentGatewayFake(payment),
        saver,
        tx,
    )

    result = await interactor.execute(create_input())

    assert result.id == payment.id
    assert saver.saved == []
    assert tx.committed == 0


async def test_read_payment_returns_payment() -> None:
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
    )
    result = await ReadPaymentInteractor(PaymentGatewayFake(payment)).execute(
        payment.id,
    )

    assert result.id == payment.id


async def test_read_payment_raises_not_found() -> None:
    with pytest.raises(ObjectNotFoundError):
        await ReadPaymentInteractor(PaymentGatewayFake()).execute(
            uuid4(),
        )


async def test_process_payment_success_updates_status_and_sends_webhook() -> (
    None
):
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
    )
    saver = EntitySaverFake()
    webhook = WebhookSenderFake()
    tx = TransactionManagerFake()
    interactor = ProcessPaymentInteractor(
        PaymentGatewayFake(payment),
        PaymentGatewayEmulatorFake(True),
        saver,
        tx,
    )

    result = await interactor.execute(payment.id)

    assert result.status == PaymentStatus.SUCCEEDED
    assert payment.processed_at is not None
    assert webhook.sent == []
    assert len(saver.saved) == 1
    assert isinstance(saver.saved[0], OutboxEvent)
    assert saver.saved[0].event_type == "payments.webhook"
    assert saver.saved[0].payload == {"payment_id": str(payment.id)}
    assert tx.committed == 1


async def test_process_payment_gateway_failure_marks_failed() -> None:
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
    )
    saver = EntitySaverFake()
    interactor = ProcessPaymentInteractor(
        PaymentGatewayFake(payment),
        PaymentGatewayEmulatorFake(False),
        saver,
        TransactionManagerFake(),
    )

    result = await interactor.execute(payment.id)

    assert result.status == PaymentStatus.FAILED
    assert len(saver.saved) == 1
    assert isinstance(saver.saved[0], OutboxEvent)
    assert saver.saved[0].event_type == "payments.webhook"


async def test_process_payment_skips_webhook_outbox_when_url_is_empty() -> (
    None
):
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="",
    )
    saver = EntitySaverFake()
    tx = TransactionManagerFake()
    interactor = ProcessPaymentInteractor(
        PaymentGatewayFake(payment),
        PaymentGatewayEmulatorFake(True),
        saver,
        tx,
    )

    result = await interactor.execute(payment.id)

    assert result.status == PaymentStatus.SUCCEEDED
    assert saver.saved == []
    assert tx.committed == 1
    assert tx.rolled_back == 0


async def test_send_webhook_sends_existing_payment() -> None:
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
    )
    webhook = WebhookSenderFake()
    interactor = SendWebhookInteractor(PaymentGatewayFake(payment), webhook)

    await interactor.execute(payment.id)

    assert len(webhook.sent) == 1
    assert webhook.sent[0].id == payment.id


async def test_send_webhook_skips_empty_webhook_url() -> None:
    payment = Payment(
        amount=Money(Decimal("10.00"), Currency.RUB),
        description="Invoice",
        metadata={},
        idempotency_key="key-1",
        webhook_url="",
    )
    webhook = WebhookSenderFake()
    interactor = SendWebhookInteractor(PaymentGatewayFake(payment), webhook)

    await interactor.execute(payment.id)

    assert webhook.sent == []


async def test_send_webhook_raises_not_found() -> None:
    interactor = SendWebhookInteractor(
        PaymentGatewayFake(),
        WebhookSenderFake(),
    )

    with pytest.raises(ObjectNotFoundError):
        await interactor.execute(uuid4())
