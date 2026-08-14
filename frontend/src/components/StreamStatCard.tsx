import type { StreamMetrics } from "@/hooks/useTelemetryStream";
import { Activity } from "lucide-react";

interface StreamStatCardProps {
  streamName: string;
  metrics: StreamMetrics;
}

export function StreamStatCard({ streamName, metrics }: StreamStatCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="text-sm font-semibold text-slate-200">{streamName}</span>
        <Activity className="w-4 h-4 text-blue-400" />
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <span className="text-slate-500 block">Length</span>
          <span className="font-mono text-slate-200">{metrics.length}</span>
        </div>
        <div>
          <span className="text-slate-500 block">Pending</span>
          <span className="font-mono text-amber-400">{metrics.pending}</span>
        </div>
        <div>
          <span className="text-slate-500 block">Oldest Age</span>
          <span className="font-mono text-slate-200">
            {metrics.oldest_pending_age_sec == null
              ? "—"
              : `${metrics.oldest_pending_age_sec}s`}
          </span>
        </div>
      </div>
    </div>
  );
}
