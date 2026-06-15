from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue
from faststream.rabbit.schemas.queue import QueueType

PAYMENTS_NEW_ROUTING_KEY = "payments.new"
PAYMENTS_NEW_DLQ_ROUTING_KEY = "payments.new.dlq"
PAYMENTS_WEBHOOK_ROUTING_KEY = "payments.webhook"
PAYMENTS_WEBHOOK_DLQ_ROUTING_KEY = "payments.webhook.dlq"

payments_exchange = RabbitExchange(
    "payments",
    durable=True,
)
payments_dead_letter_exchange = RabbitExchange(
    "payments.dlx",
    durable=True,
)
payments_new_dlq = RabbitQueue(
    PAYMENTS_NEW_DLQ_ROUTING_KEY,
    durable=True,
    routing_key=PAYMENTS_NEW_DLQ_ROUTING_KEY,
)
payments_webhook_dlq = RabbitQueue(
    PAYMENTS_WEBHOOK_DLQ_ROUTING_KEY,
    durable=True,
    routing_key=PAYMENTS_WEBHOOK_DLQ_ROUTING_KEY,
)
payments_new_queue = RabbitQueue(
    PAYMENTS_NEW_ROUTING_KEY,
    queue_type=QueueType.QUORUM,
    durable=True,
    routing_key=PAYMENTS_NEW_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": payments_dead_letter_exchange.name,
        "x-dead-letter-routing-key": PAYMENTS_NEW_DLQ_ROUTING_KEY,
        "x-delivery-limit": 3,
    },
)
payments_webhook_queue = RabbitQueue(
    PAYMENTS_WEBHOOK_ROUTING_KEY,
    queue_type=QueueType.QUORUM,
    durable=True,
    routing_key=PAYMENTS_WEBHOOK_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": payments_dead_letter_exchange.name,
        "x-dead-letter-routing-key": PAYMENTS_WEBHOOK_DLQ_ROUTING_KEY,
        "x-delivery-limit": 3,
    },
)


async def declare_payments_topology(broker: RabbitBroker) -> None:
    await broker.declare_exchange(payments_exchange)
    await broker.declare_exchange(payments_dead_letter_exchange)
    await broker.declare_queue(payments_new_queue)
    await broker.declare_queue(payments_new_dlq)
    await broker.declare_queue(payments_webhook_queue)
    await broker.declare_queue(payments_webhook_dlq)
