# Payments Processing Service

Async payment-processing service for the test assignment.

## Stack

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 async + PostgreSQL
- RabbitMQ + FastStream
- Alembic
- Docker Compose

## Run

```bash
docker compose up --build
```

The API is available at `http://payments.localhost/api/v1` through Traefik
and at `http://localhost:8000/api/v1` directly.
The Traefik dashboard is available at `http://traefik.payments.localhost`.
RabbitMQ management UI is available at `http://localhost:15672`
with `guest` / `guest`.

Local development:

```bash
uv sync
docker compose up postgres rabbitmq
alembic upgrade head
python -m payments --app
python -m payments --scheduler
python -m payments --consumer
```

## Environment

- `API_KEY`: static API key for `X-API-Key`; local default is
  `dev-api-key`.
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`,
  `POSTGRES_PASSWORD`, `POSTGRES_DB`: PostgreSQL connection settings.
- `RABBITMQ_URL`: RabbitMQ URL.
- `OUTBOX_SCHEDULER_INTERVAL_SECONDS`: outbox polling interval.
- `OUTBOX_SCHEDULER_BATCH_SIZE`: outbox batch size.
- `WEBHOOK_TIMEOUT_SECONDS`: timeout for webhook calls.

## API Examples

Create payment:

```bash
curl -i -X POST http://payments.localhost/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -H "Idempotency-Key: order-42" \
  -d '{
    "amount": "100.50",
    "currency": "RUB",
    "description": "Order 42",
    "metadata": {"order_id": "42"},
    "webhook_url": "https://example.com/payments/webhook"
  }'
```

Response:

```json
{
  "payment_id": "00000000-0000-0000-0000-000000000000",
  "status": "pending",
  "created_at": "2026-06-15T12:00:00Z"
}
```

Read payment:

```bash
curl -i http://payments.localhost/api/v1/payments/00000000-0000-0000-0000-000000000000 \
  -H "X-API-Key: dev-api-key"
```

## Processing

`POST /api/v1/payments` stores a pending payment and an outbox event in
one database transaction. The outbox scheduler publishes the event to the
RabbitMQ `payments.new` queue. The consumer receives the message, emulates
payment gateway processing with a 2-5 second delay and 90% success rate,
updates the payment status, and sends a webhook.

`payments.new` is declared as a RabbitMQ quorum queue with delivery limit
`3`. If the consumer fails, FastStream nacks the message. After 3 failed
deliveries RabbitMQ moves it to `payments.new.dlq` through the
`payments.dlx` dead-letter exchange.

Webhook payload:

```json
{
  "payment_id": "00000000-0000-0000-0000-000000000000",
  "status": "succeeded",
  "amount": "100.50",
  "currency": "RUB",
  "description": "Order 42",
  "metadata": {"order_id": "42"},
  "created_at": "2026-06-15T12:00:00Z",
  "processed_at": "2026-06-15T12:00:04Z"
}
```

## Scenarios

### Scenario: create payment

Request 1.

- Public URL: `POST /api/v1/payments`
- Request body:

```json
{
  "amount": "100.50",
  "currency": "RUB",
  "description": "Order 42",
  "metadata": {"order_id": "42"},
  "webhook_url": "https://example.com/payments/webhook"
}
```

- Required headers: `X-API-Key`, `Idempotency-Key`
- Response body:

```json
{
  "payment_id": "00000000-0000-0000-0000-000000000000",
  "status": "pending",
  "created_at": "2026-06-15T12:00:00Z"
}
```

- Side effects: `payments` inserts one row with status `pending`;
  `outbox_events` inserts one event with topic `payments.new` and payload
  `{"payment_id": "<payment_id>"}`. The outbox scheduler publishes the
  event to RabbitMQ. The `payments` consumer processes it, updates the
  payment status to `succeeded` or `failed`, sets `processed_at`, and sends
  an HTTP webhook to `webhook_url`. No SMTP integration is used.

### Scenario: create payment with duplicate idempotency key

Request 1.

- Public URL: `POST /api/v1/payments`
- Request body: same as the original request
- Required headers: same `X-API-Key` and same `Idempotency-Key`
- Response body: same `payment_id`, current status, and original
  `created_at`
- Side effects: no new `payments` row and no new `outbox_events` row are
  created. No new consuming-service call or webhook is scheduled by this
  duplicate request.

### Scenario: get payment

Request 1.

- Public URL: `GET /api/v1/payments/{payment_id}`
- Request body: none
- Required headers: `X-API-Key`
- Response body:

```json
{
  "payment_id": "00000000-0000-0000-0000-000000000000",
  "amount": "100.50",
  "currency": "RUB",
  "description": "Order 42",
  "metadata": {"order_id": "42"},
  "status": "succeeded",
  "idempotency_key": "order-42",
  "webhook_url": "https://example.com/payments/webhook",
  "created_at": "2026-06-15T12:00:00Z",
  "processed_at": "2026-06-15T12:00:04Z"
}
```

- Side effects: no database changes, no outbox event, no consuming-service
  call, and no external integration call.

## Validation

```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q tests
```
