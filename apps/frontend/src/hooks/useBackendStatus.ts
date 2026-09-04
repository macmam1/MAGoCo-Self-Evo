import { useEffect, useState } from "react";
import { API_URL } from "@/config";

export interface BackendStatus {
  online: boolean;
  version?: string;
  tools?: number;
  checkedAt: number;
}

/** Polls GET /health so the shell always shows real backend state. */
export function useBackendStatus(intervalMs = 30000) {
  const [status, setStatus] = useState<BackendStatus>({
    online: false,
    checkedAt: 0,
  });

  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const r = await fetch(`${API_URL}/health`);
        const j = await r.json();
        if (alive)
          setStatus({
            online: r.ok,
            version: j.version,
            tools: j.tools_available,
            checkedAt: Date.now(),
          });
      } catch {
        if (alive) setStatus({ online: false, checkedAt: Date.now() });
      }
    };
    check();
    const t = setInterval(check, intervalMs);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [intervalMs]);

  return status;
}
