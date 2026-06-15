from typing import AsyncIterator
from unittest.mock import AsyncMock

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

from payments.application.queries.healthcheck.dto import HealthStatus
from payments.application.queries.healthcheck.interactor import (
    HealthCheckInteractor,
)
from payments.config import Config
from tests.conftest import TestProvider


class TestHealthProvider(Provider):
    __test__ = False
    interactor = from_context(
        provides=HealthCheckInteractor,
        scope=Scope.RUNTIME,
    )


@pytest.fixture
def health_interactor_mock(request: pytest.FixtureRequest) -> AsyncMock:
    interactor = AsyncMock(spec=HealthCheckInteractor)
    interactor.execute.return_value = HealthStatus(
        status="OK" if request.param else "FAILURE",
    )
    return interactor


@pytest_asyncio.fixture
async def container(
    config: Config,
    health_interactor_mock: AsyncMock,
) -> AsyncIterator[AsyncContainer]:
    container = make_async_container(
        TestProvider(),
        TestHealthProvider(),
        context={
            Config: config,
            HealthCheckInteractor: health_interactor_mock,
        },
        start_scope=Scope.RUNTIME,
    )
    yield container
    await container.close()


@pytest.mark.parametrize("health_interactor_mock", [True], indirect=True)
def test_health_contract(http_client: TestClient) -> None:
    response = http_client.get("/health")
    response.raise_for_status()
    data = response.json()
    assert data["status"] is True


@pytest.mark.parametrize("health_interactor_mock", [False], indirect=True)
def test_health_returns_503(http_client: TestClient) -> None:
    response = http_client.get("/health")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
