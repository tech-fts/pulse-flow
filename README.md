# ⚡ DispatchOS (`dispatch-os`)

> High-Throughput Event-Driven Notification Engine & LLM Digest Pipeline

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-000000.svg?style=flat&logo=next.js)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1.svg?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D.svg?style=flat&logo=redis)](https://redis.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**DispatchOS** is an enterprise-grade notification orchestration platform built to ingest millions of events across Email, SMS, Push, and In-App channels. Designed with active load shedding, token-bucket rate limiting, LLM-driven event batching, and real-time SSE metrics.

---

## 📌 Key Architectural Features

* **High-Throughput Ingestion API:** Async FastAPI backend using Pydantic v2 validation and pipeline batching (`XADD`) to Redis Streams for instant `<10ms` response times.
* **Weighted Fair Queueing (WFQ):** Taskiq worker pools segregated into `critical` (OTPs), `standard`, and `bulk` queues to eliminate queue starvation.
* **Intelligent LLM Batcher:** PydanticAI worker aggregates non-critical user activity into a single daily summary digest, eliminating notification fatigue.
* **Dynamic Provider Fallback:** Automatic circuit breakers and rate-limited token buckets (Lua in Redis) that route around gateway failures (e.g., SendGrid $\rightarrow$ AWS SES).
* **High-Concurrency UPSERT Aggregations:** Redis memory buffers periodically flush aggregate performance metrics into PostgreSQL using optimized `asyncpg` queries.
* **Real-Time Telemetry Dashboard:** Next.js 15 App Router dashboard consuming FastAPI Server-Sent Events (SSE) for live queue health and latency tracking.

---

## 🏗️ System Architecture


```

[Inbound Events] ---> (FastAPI Ingestion) ---> [Redis Streams / Queues]
|
+-----------+-----------+
|                       |
(Priority Workers)      (LLM Batcher)
|                       |
[SendGrid / Twilio]     [PydanticAI Digest]
|                       |
+-----------+-----------+
|
(Buffered Bulk UPSERT)
v
[Next.js Dashboard] <--- (SSE Stream) <--- [PostgreSQL Metrics]

```

---

## 🛠️ Tech Stack

* **Backend:** Python 3.12, FastAPI, Taskiq, Pydantic v2, `httpx`, `asyncpg`
* **Frontend:** Next.js 15, TypeScript, Tailwind CSS, Recharts, Lucide Icons
* **Database & Cache:** PostgreSQL 16 (TimescaleDB / JSONB), Redis 7 (Streams + Lua)
* **AI Orchestration:** PydanticAI / OpenAI API

---

## 🚀 Quick Start

### Prerequisites
* Docker & Docker Compose
* Python 3.12+ / Node.js 20+ (for local dev)

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/dispatch-os.git](https://github.com/your-username/dispatch-os.git)
cd dispatch-os

```

### 2. Configure Environment Variables

Copy the template files and fill in your keys:

```bash
cp .env.example .env

```

### 3. Spin Up Infrastructure via Docker

```bash
docker-compose up -d --build

```

This starts:

* **FastAPI Backend:** `http://localhost:8000`
* **Next.js Dashboard:** `http://localhost:3000`
* **PostgreSQL:** `localhost:5432`
* **Redis:** `localhost:6379`

---

## ⚡ API Endpoints

### 1. Send Event (Inbound Ingestion)

```http
POST /api/v1/events
Content-Type: application/json

{
  "user_id": "usr_99x12a",
  "category": "security",
  "priority": "critical",
  "channel": "sms",
  "payload": {
    "title": "New Login Attempt",
    "code": "849201"
  }
}

```

### 2. Stream Real-Time Queue Telemetry (SSE)

```http
GET /api/v1/telemetry/stream
Accept: text/event-stream

```

---

## 🧪 Running Tests & Load Testing

Run backend tests using `pytest`:

```bash
docker-compose exec backend pytest -v

```

Execute Locust load-testing script (simulates 10,000 req/sec):

```bash
locust -f tests/load_test.py --host=http://localhost:8000

```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.