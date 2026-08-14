import { api } from "./api";

export interface HealthStatus {
  status: "ok" | "degraded" | "down";
  timestamp: string;
}

export async function checkHealth(): Promise<HealthStatus> {
  try {
    // /healthz is served from the backend root, not under /api/v1, so
    // override the instance's /api/v1 baseURL for this call. The request
    // still flows through the Next.js rewrite proxy defined in next.config.ts.
    const res = await api.get<{ status: string }>("/healthz", { baseURL: "/" });
    return {
      status: res.data.status === "ok" ? "ok" : "degraded",
      timestamp: new Date().toISOString(),
    };
  } catch {
    return { status: "down", timestamp: new Date().toISOString() };
  }
}
