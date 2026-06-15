from typing import Protocol

from payments.entities.entities import OutboxEvent


class OutboxPublisher(Protocol):
    async def publish(self, event: OutboxEvent) -> None: ...
