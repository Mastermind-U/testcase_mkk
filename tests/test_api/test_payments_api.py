from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from dishka import (
    AsyncContainer,
    Provider,
    Scope,
    from_context,
    make_async_container,
)
from fastapi import status
from fastapi.testclient import TestClient

from payments.application.commands.payments import CreatePaymentInteractor
from payments.application.common.payment_dto import PaymentDTO
from payments.application.queries.payments import ReadPaymentInteractor
from payments.config import Config
from payments.entities.enums import Currency, PaymentStatus
from payments.entities.exceptions import ObjectNotFoundError
from tests.conftest import TestProvider


class TestPaymentsProvider(Provider):
    __test__ = False
    create_payment_interactor = from_context(
        provides=CreatePaymentInteractor,
        scope=Scope.RUNTIME,
    )
    read_payment_interactor = from_context(
        provides=ReadPaymentInteractor,
        scope=Scope.RUNTIME,
    )


@pytest.fixture
def payment_id() -> UUID:
    return uuid4()


@pytest.fixture
def payment_dto(payment_id: UUID) -> PaymentDTO:
    return PaymentDTO(
        id=payment_id,
        amount=Decimal("10.00"),
        currency=Currency.RUB,
        description="Invoice",
        metadata={"order_id": "42"},
        status=PaymentStatus.PENDING,
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
        created_at=datetime(2026, 6, 15, 12, 0, tzinfo=UTC),
        processed_at=None,
    )


@pytest.fixture
def create_payment_interactor_mock(payment_dto: PaymentDTO) -> AsyncMock:
    interactor = AsyncMock(spec=CreatePaymentInteractor)
    interactor.execute.return_value = payment_dto
    return interactor


@pytest.fixture
def read_payment_interactor_mock(payment_dto: PaymentDTO) -> AsyncMock:
    interactor = AsyncMock(spec=ReadPaymentInteractor)
    interactor.execute.return_value = payment_dto
    return interactor


@pytest_asyncio.fixture
async def container(
    config: Config,
    create_payment_interactor_mock: AsyncMock,
    read_payment_interactor_mock: AsyncMock,
) -> AsyncIterator[AsyncContainer]:
    container = make_async_container(
        TestProvider(),
        TestPaymentsProvider(),
        context={
            Config: config,
            CreatePaymentInteractor: create_payment_interactor_mock,
            ReadPaymentInteractor: read_payment_interactor_mock,
        },
        start_scope=Scope.RUNTIME,
    )
    yield container
    await container.close()


def payment_body() -> dict[str, object]:
    return {
        "amount": "10.00",
        "currency": "RUB",
        "description": "Invoice",
        "metadata": {"order_id": "42"},
        "webhook_url": "https://example.com/webhook",
    }


def auth_headers(config: Config) -> dict[str, str]:
    return {
        "X-API-Key": config.API_KEY,
        "Idempotency-Key": "key-1",
    }


def test_create_payment_contract(
    http_client: TestClient,
    config: Config,
    payment_id: UUID,
) -> None:
    response = http_client.post(
        "/api/v1/payments",
        headers=auth_headers(config),
        json=payment_body(),
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {
        "payment_id": str(payment_id),
        "status": "pending",
        "created_at": "2026-06-15T12:00:00Z",
    }


def test_create_payment_accepts_null_webhook_url(
    http_client: TestClient,
    config: Config,
) -> None:
    body = payment_body()
    body["webhook_url"] = None

    response = http_client.post(
        "/api/v1/payments",
        headers=auth_headers(config),
        json=body,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED


def test_create_payment_rejects_invalid_webhook_url(
    http_client: TestClient,
    config: Config,
) -> None:
    body = payment_body()
    body["webhook_url"] = "not-a-url"

    response = http_client.post(
        "/api/v1/payments",
        headers=auth_headers(config),
        json=body,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_payment_duplicate_idempotency_returns_same_payment(
    http_client: TestClient,
    config: Config,
    payment_id: UUID,
) -> None:
    first = http_client.post(
        "/api/v1/payments",
        headers=auth_headers(config),
        json=payment_body(),
    )
    second = http_client.post(
        "/api/v1/payments",
        headers=auth_headers(config),
        json=payment_body(),
    )

    assert first.status_code == status.HTTP_202_ACCEPTED
    assert second.status_code == status.HTTP_202_ACCEPTED
    assert first.json()["payment_id"] == str(payment_id)
    assert second.json()["payment_id"] == str(payment_id)


def test_create_payment_requires_api_key(
    http_client: TestClient,
    config: Config,
) -> None:
    headers = auth_headers(config)
    headers.pop("X-API-Key")

    response = http_client.post(
        "/api/v1/payments",
        headers=headers,
        json=payment_body(),
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_payment_rejects_wrong_api_key(
    http_client: TestClient,
    config: Config,
) -> None:
    headers = auth_headers(config)
    headers["X-API-Key"] = "wrong"

    response = http_client.post(
        "/api/v1/payments",
        headers=headers,
        json=payment_body(),
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_payment_requires_idempotency_key(
    http_client: TestClient,
    config: Config,
) -> None:
    headers = auth_headers(config)
    headers.pop("Idempotency-Key")

    response = http_client.post(
        "/api/v1/payments",
        headers=headers,
        json=payment_body(),
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_payment_rejects_invalid_currency(
    http_client: TestClient,
    config: Config,
) -> None:
    body = payment_body()
    body["currency"] = "GBP"

    response = http_client.post(
        "/api/v1/payments",
        headers=auth_headers(config),
        json=body,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_payment_rejects_invalid_amount(
    http_client: TestClient,
    config: Config,
) -> None:
    body = payment_body()
    body["amount"] = "-1.00"

    response = http_client.post(
        "/api/v1/payments",
        headers=auth_headers(config),
        json=body,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_payment_contract(
    http_client: TestClient,
    config: Config,
    payment_id: UUID,
) -> None:
    response = http_client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": config.API_KEY},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["payment_id"] == str(payment_id)
    assert response.json()["amount"] == "10.00"
    assert response.json()["currency"] == "RUB"
    assert response.json()["status"] == "pending"


def test_get_payment_requires_api_key(
    http_client: TestClient,
    payment_id: UUID,
) -> None:
    response = http_client.get(f"/api/v1/payments/{payment_id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_payment_returns_404(
    http_client: TestClient,
    config: Config,
    read_payment_interactor_mock: AsyncMock,
    payment_id: UUID,
) -> None:
    read_payment_interactor_mock.execute.side_effect = ObjectNotFoundError

    response = http_client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": config.API_KEY},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
