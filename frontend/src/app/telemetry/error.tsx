"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default function TelemetryError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Telemetry Route Error:", error);
  }, [error]);

  return (
    <div className="p-12 max-w-lg mx-auto text-center space-y-4">
      <div className="p-3 bg-rose-950/50 border border-rose-800 rounded-full w-fit mx-auto text-rose-400">
        <AlertTriangle className="w-8 h-8" />
      </div>
      <h2 className="text-xl font-bold text-slate-100">Telemetry Stream Error</h2>
      <p className="text-sm text-slate-400">
        {error.message || "An unexpected error occurred while rendering real-time telemetry."}
      </p>
      <button
        onClick={() => reset()}
        className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium transition"
      >
        <RotateCcw className="w-4 h-4" />
        <span>Retry Connection</span>
      </button>
    </div>
  );
}
