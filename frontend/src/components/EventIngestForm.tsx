"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, Send } from "lucide-react";

import {
  EVENT_CHANNELS,
  EVENT_PRIORITIES,
  sendTelemetryEvent,
} from "@/lib/events";

type Status = { type: "success" | "error"; message: string } | null;

export default function EventIngestForm() {
  const [userId, setUserId] = useState("user-123");
  const [category, setCategory] = useState("system_alert");
  const [priority, setPriority] = useState<string>("critical");
  const [channel, setChannel] = useState<string>("sms");
  const [payload, setPayload] = useState('{"metric": "cpu_load", "val": 88}');
  const [status, setStatus] = useState<Status>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus(null);

    let parsedPayload: Record<string, unknown>;
    try {
      parsedPayload = JSON.parse(payload);
    } catch {
      setStatus({ type: "error", message: "Payload must be valid JSON" });
      return;
    }

    setLoading(true);
    try {
      const result = await sendTelemetryEvent({
        user_id: userId,
        category,
        priority: priority as (typeof EVENT_PRIORITIES)[number],
        channel: channel as (typeof EVENT_CHANNELS)[number],
        payload: parsedPayload,
      });
      setStatus({
        type: "success",
        message: `Accepted (202) — event ${result.event_id} enqueued to "${result.queue}"`,
      });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const errorMsg =
        typeof detail === "string" ? detail : err.message || "Failed to ingest event";
      setStatus({
        type: "error",
        message: `Error (${err.response?.status || 500}): ${errorMsg}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    "w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500";
  const labelClass = "block text-sm font-medium text-slate-400 mb-1";

  return (
    <div className="p-6 bg-slate-900 rounded-xl border border-slate-800 space-y-4">
      <h2 className="text-lg font-semibold text-slate-100">
        Ingest Notification Event
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>User ID</label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className={inputClass}
              required
            />
          </div>
          <div>
            <label className={labelClass}>Category</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className={inputClass}
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className={inputClass}
            >
              {EVENT_PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Channel</label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className={inputClass}
            >
              {EVENT_CHANNELS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className={labelClass}>JSON Payload</label>
          <textarea
            rows={3}
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            className={`${inputClass} font-mono`}
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm font-medium disabled:opacity-50 transition"
        >
          <Send className="w-4 h-4" />
          {loading ? "Sending..." : "Emit Event"}
        </button>
      </form>

      {status && (
        <div
          className={`flex items-center gap-2 p-3 rounded text-sm ${
            status.type === "success"
              ? "bg-green-950/50 text-green-400 border border-green-800"
              : "bg-red-950/50 text-red-400 border border-red-800"
          }`}
        >
          {status.type === "success" ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
          <span>{status.message}</span>
        </div>
      )}
    </div>
  );
}
