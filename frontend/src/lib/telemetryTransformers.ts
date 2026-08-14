import type { StreamMetrics, TelemetryFrame } from "@/hooks/useTelemetryStream";

export interface FlattenedChartPoint {
  timestamp: string;
  [metricKey: string]: string | number;
}

/**
 * Transforms SSE payloads into flat objects for Recharts rendering.
 */
export function transformFramesForChart(
  frames: TelemetryFrame[],
  metricKey: keyof StreamMetrics = "pending"
): FlattenedChartPoint[] {
  return frames.map((frame) => {
    const point: FlattenedChartPoint = { timestamp: frame.timestamp };

    Object.entries(frame.payload).forEach(([streamName, metrics]) => {
      point[streamName] = metrics[metricKey];
    });

    return point;
  });
}
