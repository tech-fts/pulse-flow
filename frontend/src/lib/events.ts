import { api } from "./api";

// Values mirror the backend EventPriority / EventChannel enums
// (backend/app/schemas/event.py).
export const EVENT_PRIORITIES = ["critical", "standard", "bulk"] as const;
export type EventPriority = (typeof EVENT_PRIORITIES)[number];

export const EVENT_CHANNELS = ["email", "sms", "push", "in_app"] as const;
export type EventChannel = (typeof EVENT_CHANNELS)[number];

// Matches the backend EventIngest schema. Note: extra fields are forbidden
// server-side (extra="forbid"), so the shape must match exactly.
export interface IngestEvent {
  user_id: string;
  category: string;
  priority: EventPriority;
  channel: EventChannel;
  payload: Record<string, unknown>;
}

// Matches the backend EventResponse schema.
export interface IngestResponse {
  event_id: string;
  queue: string;
  status: string;
}

/**
 * Sends a notification event to POST /api/v1/events.
 *
 * The backend requires an `Idempotency-Key` header (no default), used for
 * outbox deduplication — a fresh UUID per request is safe.
 */
export async function sendTelemetryEvent(event: IngestEvent): Promise<IngestResponse> {
  const response = await api.post<IngestResponse>("/events", event, {
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
  return response.data;
}
