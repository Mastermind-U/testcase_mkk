import inspect

from faststream.rabbit import RabbitBroker

from payments.application.commands.outbox_processor.publisher import (
    OutboxPublisher,
)
from payments.entities.entities import OutboxEvent


class FaststreamRabbitOutboxPublisher(OutboxPublisher):
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, event: OutboxEvent) -> None:
        published = self._broker.publish(
            event.payload,
            queue=event.event_type,
            correlation_id=str(event.id),
        )
        if inspect.isawaitable(published):
            await published
