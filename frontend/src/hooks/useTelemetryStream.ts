import { useEffect, useState } from "react";

export interface StreamMetrics {
  length: number;
  pending: number;
  // Backend emits null when a stream has no pending entries.
  oldest_pending_age_sec: number | null;
}

export type TelemetryPayload = Record<string, StreamMetrics>;

export interface TelemetryFrame {
  timestamp: string;
  payload: TelemetryPayload;
}

interface UseTelemetryStreamOptions {
  url: string;
  maxPoints?: number;
}

export function useTelemetryStream({ url, maxPoints = 30 }: UseTelemetryStreamOptions) {
  const [data, setData] = useState<TelemetryFrame[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event: MessageEvent) => {
      try {
        const payload: TelemetryPayload = JSON.parse(event.data);
        const newFrame: TelemetryFrame = {
          timestamp: new Date().toLocaleTimeString(),
          payload,
        };

        setData((prev) => [...prev.slice(-(maxPoints - 1)), newFrame]);
      } catch (err) {
        setError("Failed to parse incoming frame");
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      setError("SSE Connection Lost");
    };

    return () => {
      eventSource.close();
    };
  }, [url, maxPoints]);

  return { data, isConnected, error };
}
