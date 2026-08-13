# Backend Routes (API Reference)

Base URL: `http://localhost:8000` (Docker Compose backend service on port `8000`).

All application endpoints are namespaced under `/api/v1`. Two additional
endpoints (`/healthz`, `/readyz`) are infrastructure probes, not part of the
public API surface.

---

## Route summary

| Method | Path                       | Audience   | Description                          |
|--------|----------------------------|------------|--------------------------------------|
| POST   | `/api/v1/events`           | frontend   | Ingest a notification event          |
| GET    | `/api/v1/telemetry/stream` | frontend   | SSE stream of live queue telemetry   |
| GET    | `/healthz`                 | infra      | Liveness probe                       |
| GET    | `/readyz`                 | infra      | Readiness probe (Redis + PostgreSQL) |

---

## 1. Ingest Event

```
POST /api/v1/events
```

Accept a notification event. Critical events are queued for immediate delivery;
standard/bulk events are buffered into the daily LLM digest.

### Headers

| Header           | Required | Description                              |
|------------------|----------|------------------------------------------|
| `Content-Type`   | yes      | `application/json`                       |
| `Idempotency-Key`| yes      | Client-generated unique key (dedup)      |

### Request body

```json
{
  "user_id":  "usr_99x12a",
  "category": "security",
  "priority": "critical",
  "channel":  "sms",
  "payload": {
    "title": "New Login Attempt",
    "code":  "849201"
  }
}
```

| Field      | Type   | Constraints                          | Default     |
|------------|--------|--------------------------------------|-------------|
| `user_id`  | string | 1–128 chars                          | —           |
| `category` | string | 1–64 chars (used for template lookup)| —           |
| `priority` | enum   | `critical` \| `standard` \| `bulk`   | `standard`  |
| `channel`  | enum   | `email` \| `sms` \| `push` \| `in_app` | `sms`    |
| `payload`  | object | non-empty; unknown fields rejected   | —           |

### Response — `202 Accepted`

```json
{
  "event_id": "0d3c7f2e-…",
  "queue":    "stream:critical",
  "status":   "accepted"
}
```

`queue` is `stream:<priority>` for critical events and `digest` for
standard/bulk events.

### Error responses

| Status | Meaning                                              |
|--------|------------------------------------------------------|
| `422`  | Invalid body, empty payload, or missing `Idempotency-Key` header |
| `409`  | `Idempotency-Key` reused with a different request body |
| `429`  | Per-tenant rate limit exceeded (default 100 req/s)   |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "user_id": "usr_99x12a",
    "category": "security",
    "priority": "critical",
    "channel": "sms",
    "payload": {"title": "New Login Attempt", "code": "849201"}
  }'
```

---

## 2. Telemetry Stream (SSE)

```
GET /api/v1/telemetry/stream
```

Server-Sent Events stream emitting queue-health metrics once per second.

### Headers

| Header     | Required | Description             |
|------------|----------|-------------------------|
| `Accept`   | no       | `text/event-stream`     |

### Stream format

Each frame is a `data:` line containing JSON keyed by stream name:

```json
{
  "stream:critical":    {"length": 12,  "pending": 3, "oldest_pending_age_sec": 4.2},
  "stream:standard":    {"length": 40,  "pending": 0, "oldest_pending_age_sec": null},
  "stream:bulk":        {"length": 120, "pending": 0, "oldest_pending_age_sec": null},
  "stream:dead_letter": {"length": 2,   "pending": 0, "oldest_pending_age_sec": null}
}
```

| Field                    | Meaning                                    |
|--------------------------|--------------------------------------------|
| `length`                 | Total entries in the stream (backlog)      |
| `pending`                | Entries delivered but not yet acked        |
| `oldest_pending_age_sec` | Idle age of the oldest pending entry (or `null`) |

### Example

```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/api/v1/telemetry/stream
```

---

## 3. Liveness Probe

```
GET /healthz
```

Always returns `200` while the process is up.

```json
{"status": "ok"}
```

---

## 4. Readiness Probe

```
GET /readyz
```

Returns `200` when Redis and PostgreSQL are reachable, `503` otherwise.

```json
{
  "status": "ready",
  "checks": {"redis": true, "database": true}
}
```

When any dependency is down, `status` is `unavailable` and the corresponding
`checks` entry is `false`.

---

## CORS

`CORS_ORIGINS` defaults to `http://localhost:3000` (the Next.js dev server).
Allowed methods: `GET`, `POST`, `OPTIONS`. Allowed headers: `Authorization`,
`Content-Type`, `Idempotency-Key`, `X-Request-ID`.

> Set explicit origins (no `*`) when running in production — the settings
> validator enforces this.
