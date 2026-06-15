from unittest.mock import AsyncMock

from payments.application.queries.healthcheck.gateway import (
    HealthCheckGateway,
)
from payments.application.queries.healthcheck.interactor import (
    HealthCheckInteractor,
)


async def test_healthcheck_int_returns_ok_when_database_is_available() -> None:
    gw = AsyncMock(spec=HealthCheckGateway)
    gw.check_database.return_value = True
    interactor = HealthCheckInteractor(gw)

    result = await interactor.execute()

    assert result.status == "OK"
    gw.check_database.assert_awaited_once()


async def test_healthcheck_int_failure_when_database_is_unavailable() -> None:
    gw = AsyncMock(spec=HealthCheckGateway)
    gw.check_database.return_value = False
    interactor = HealthCheckInteractor(gw)

    result = await interactor.execute()

    assert result.status == "FAILURE"
    gw.check_database.assert_awaited_once()
