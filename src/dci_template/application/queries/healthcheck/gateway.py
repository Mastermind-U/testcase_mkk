from typing import Protocol


class HealthCheckGateway(Protocol):
    async def check_database(self) -> bool: ...
