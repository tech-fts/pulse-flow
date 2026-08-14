"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface TelemetryFrame {
  timestamp: string;
  [streamName: string]: any;
}

export default function TelemetryStream() {
  const [data, setData] = useState<TelemetryFrame[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Connect to backend SSE endpoint (proxied via next.config.ts rewrites)
    const eventSource = new EventSource("/api/v1/telemetry/stream");

    eventSource.onopen = () => setConnected(true);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const timeStr = new Date().toLocaleTimeString();

        setData((prevData) => {
          // Keep a sliding window of the last 30 data points
          const updated = [...prevData, { timestamp: timeStr, ...payload }];
          return updated.slice(-30);
        });
      } catch (err) {
        console.error("Failed to parse SSE frame:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("SSE Connection error:", err);
      setConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-2">
        <span
          className={`h-3 w-3 rounded-full ${
            connected ? "bg-green-500 animate-pulse" : "bg-red-500"
          }`}
        />
        <span className="text-sm font-medium">
          {connected ? "Live Stream Connected" : "Disconnected"}
        </span>
      </div>

      <div className="h-64 w-full bg-slate-900/50 p-4 rounded-xl border border-slate-800">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <XAxis dataKey="timestamp" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155" }}
            />
            {/* Example line for critical stream pending count */}
            <Area
              type="monotone"
              dataKey="stream:critical.pending"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
