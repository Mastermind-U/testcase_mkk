from typing import Protocol

from dci_template.entities.entities import OutboxEvent


class OutboxPublisher(Protocol):
    async def publish(self, event: OutboxEvent) -> None: ...
