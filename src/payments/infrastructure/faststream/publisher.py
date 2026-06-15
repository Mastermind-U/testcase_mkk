import inspect

from faststream.rabbit import RabbitBroker

from payments.application.commands.outbox_processor.publisher import (
    OutboxPublisher,
)
from payments.entities.entities import OutboxEvent
from payments.infrastructure.faststream.rabbit import (
    declare_payments_topology,
    payments_exchange,
)


class FaststreamRabbitOutboxPublisher(OutboxPublisher):
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker
        self._topology_declared = False

    async def publish(self, event: OutboxEvent) -> None:
        if not self._topology_declared:
            await declare_payments_topology(self._broker)
            self._topology_declared = True

        published = self._broker.publish(
            event.payload,
            queue=event.event_type,
            exchange=payments_exchange,
            routing_key=event.event_type,
            correlation_id=str(event.id),
            persist=True,
        )
        if inspect.isawaitable(published):
            await published
