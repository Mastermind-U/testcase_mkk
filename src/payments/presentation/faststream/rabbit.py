from faststream.rabbit import RabbitExchange, RabbitQueue
from faststream.rabbit.schemas.queue import QueueType

PAYMENTS_NEW_ROUTING_KEY = "payments.new"
PAYMENTS_NEW_DLQ_ROUTING_KEY = "payments.new.dlq"
PAYMENTS_WEBHOOK_ROUTING_KEY = "payments.webhook"
PAYMENTS_WEBHOOK_DLQ_ROUTING_KEY = "payments.webhook.dlq"

payments_exchange = RabbitExchange(
    "payments",
    durable=True,
)
payments_new_queue = RabbitQueue(
    PAYMENTS_NEW_ROUTING_KEY,
    queue_type=QueueType.QUORUM,
    durable=True,
    routing_key=PAYMENTS_NEW_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
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
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": PAYMENTS_WEBHOOK_DLQ_ROUTING_KEY,
        "x-delivery-limit": 3,
    },
)
