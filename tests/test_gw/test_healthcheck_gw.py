import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from payments.infrastructure.sa.pg.gateways.healthcheck_gw import (
    SAPGHealthCheckGateway,
)


@pytest_asyncio.fixture
async def hc_gw(session: AsyncSession) -> SAPGHealthCheckGateway:
    return SAPGHealthCheckGateway(session)


async def test_healthcheck_gateway_checks_database(
    hc_gw: SAPGHealthCheckGateway,
) -> None:
    assert await hc_gw.check_database() is True
