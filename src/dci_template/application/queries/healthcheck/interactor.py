from .dto import HealthStatus
from .gateway import HealthCheckGateway


class HealthCheckInteractor:
    def __init__(self, gw: HealthCheckGateway) -> None:
        self._gw = gw

    async def execute(self) -> HealthStatus:
        db_status = await self._gw.check_database()
        return HealthStatus(status="OK" if db_status else "FAILURE")
