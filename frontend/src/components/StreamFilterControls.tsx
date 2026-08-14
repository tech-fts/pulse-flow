"use client";

interface StreamFilterControlsProps {
  availableStreams: string[];
  activeStreams: string[];
  onToggleStream: (streamName: string) => void;
}

export function StreamFilterControls({
  availableStreams,
  activeStreams,
  onToggleStream,
}: StreamFilterControlsProps) {
  if (availableStreams.length === 0) return null;

  return (
    <div className="flex items-center gap-2 flex-wrap text-xs">
      <span className="text-slate-500 font-medium">Active Streams:</span>
      {availableStreams.map((stream) => {
        const isActive = activeStreams.includes(stream);
        return (
          <button
            key={stream}
            onClick={() => onToggleStream(stream)}
            className={`px-2.5 py-1 rounded-full border transition font-mono ${
              isActive
                ? "bg-blue-950/60 border-blue-700 text-blue-300"
                : "bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300"
            }`}
          >
            {stream}
          </button>
        );
      })}
    </div>
  );
}
