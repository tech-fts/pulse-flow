import { useState, useEffect } from "react";
import { checkHealth, HealthStatus } from "@/lib/health";

export function useBackendHealth(pollIntervalMs = 15000) {
  const [health, setHealth] = useState<HealthStatus>({ status: "ok", timestamp: "" });

  useEffect(() => {
    let isMounted = true;

    const runCheck = async () => {
      const res = await checkHealth();
      if (isMounted) setHealth(res);
    };

    runCheck();
    const interval = setInterval(runCheck, pollIntervalMs);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [pollIntervalMs]);

  return health;
}
