"use client";

import { useTelemetryStream } from "@/hooks/useTelemetryStream";
import { transformFramesForChart } from "@/lib/telemetryTransformers";
import { StreamStatCard } from "@/components/StreamStatCard";
import EventIngestForm from "@/components/EventIngestForm";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function TelemetryDashboard() {
  const { data: frames, isConnected, error } = useTelemetryStream({
    url: "/api/v1/telemetry/stream",
    maxPoints: 30,
  });

  const chartData = transformFramesForChart(frames, "pending");
  const latestFrame = frames[frames.length - 1]?.payload || {};

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8 space-y-6">
      {/* Header Bar */}
      <header className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Pulse Flow Monitor</h1>
          <p className="text-sm text-slate-400">Real-time SSE event aggregation</p>
        </div>
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-full text-xs">
          <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
          <span>{isConnected ? "Connected" : "Disconnected"}</span>
        </div>
      </header>

      {error && (
        <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded text-sm">
          {error}
        </div>
      )}

      {/* Real-time Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(latestFrame).map(([streamName, metrics]) => (
          <StreamStatCard key={streamName} streamName={streamName} metrics={metrics} />
        ))}
      </section>

      {/* Main Grid: Chart + Controls */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-4 h-[380px]">
          <h2 className="text-sm font-semibold mb-4 text-slate-300">Pending Events Trend</h2>
          <ResponsiveContainer width="100%" height="90%">
            <AreaChart data={chartData}>
              <XAxis dataKey="timestamp" stroke="#475569" fontSize={11} />
              <YAxis stroke="#475569" fontSize={11} />
              <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155" }} />
              <Area type="monotone" dataKey="stream:critical" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.1} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div>
          <EventIngestForm />
        </div>
      </section>
    </main>
  );
}
