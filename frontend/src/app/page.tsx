import Link from "next/link";
import { Activity, ArrowRight, ShieldCheck, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <main className="p-8 max-w-5xl mx-auto space-y-8">
      <section className="space-y-3">
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-100">
          Pulse Flow Operational Dashboard
        </h1>
        <p className="text-slate-400 max-w-2xl text-lg">
          High-performance event ingestion pipeline and real-time streaming telemetry dashboard.
        </p>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
          <Zap className="w-6 h-6 text-amber-400" />
          <h3 className="font-semibold text-slate-200">High Throughput</h3>
          <p className="text-sm text-slate-400">
            Ingest telemetry events asynchronously with non-blocking HTTP 202 responses.
          </p>
        </div>

        <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
          <Activity className="w-6 h-6 text-blue-400" />
          <h3 className="font-semibold text-slate-200">Real-Time SSE</h3>
          <p className="text-sm text-slate-400">
            Push stream updates directly to client browsers over single HTTP connections.
          </p>
        </div>

        <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
          <ShieldCheck className="w-6 h-6 text-emerald-400" />
          <h3 className="font-semibold text-slate-200">System Resiliency</h3>
          <p className="text-sm text-slate-400">
            Automated rate-limiting, conflict resolution, and endpoint health checks.
          </p>
        </div>
      </div>

      <div className="pt-4">
        <Link
          href="/telemetry"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold transition"
        >
          <span>Launch Telemetry Stream</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </main>
  );
}
