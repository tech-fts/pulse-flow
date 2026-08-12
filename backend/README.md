# PulseFlow Backend

Event-driven notification orchestration service — high-throughput ingestion, reliable delivery pipeline, Redis Streams worker, and real-time SSE telemetry.

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 16+ and Redis 7+ (or use the included Compose stack)

## Quick Start

```bash
# 1. Create environment file
cp ../.env.example .env

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Run database migrations
alembic upgrade head

# 4. Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start a worker (separate terminal)
python -m app.workers.tasks
```

## Docker Compose

```bash
docker compose up --build
```

Starts API (:8000), worker, PostgreSQL, and Redis.

## Running Tests

```bash
pytest -v
```

## Architecture

```
[HTTP Ingest] → FastAPI → PostgreSQL (events/deliveries/outbox)
                              ↓
                        Outbox Relay
                              ↓
                        Redis Streams
                              ↓
                    [Priority Workers]
                              ↓
                    Provider Adapters → SendGrid / Twilio / AWS SES
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/events` | Ingest a notification event |
| GET | `/api/v1/telemetry/stream` | SSE queue health stream |
| GET | `/healthz` | Liveness check |
| GET | `/readyz` | Readiness check |
