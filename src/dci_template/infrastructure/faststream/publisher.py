import inspect

from faststream.kafka import KafkaBroker

from dci_template.application.commands.outbox_processor.publisher import (
    OutboxPublisher,
)
from dci_template.entities.entities import OutboxEvent


class FaststreamKafkaOutboxPublisher(OutboxPublisher):
    def __init__(self, broker: KafkaBroker) -> None:
        self._broker = broker

    async def publish(self, event: OutboxEvent) -> None:
        published = self._broker.publish(
            event.payload,
            topic=event.event_type,
            key=str(event.id),
            correlation_id=str(event.id),
        )
        if inspect.isawaitable(published):
            await published
