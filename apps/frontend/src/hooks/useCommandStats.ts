import { useEffect, useState } from "react";
import { API_URL } from "@/config";

export interface CommandStats {
  online: boolean;
  agents: number | null;
  tools: number | null;
  approvalsPending: number | null;
  providers: string[];
}

/** Live command-center stats. null = unknown (offline/loading) — never mock numbers. */
export function useCommandStats(intervalMs = 30000) {
  const [stats, setStats] = useState<CommandStats>({
    online: false,
    agents: null,
    tools: null,
    approvalsPending: null,
    providers: [],
  });

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [health, team, pending, gw] = await Promise.all([
          fetch(`${API_URL}/health`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/planning/team`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/approvals/pending`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/providers/gateway/status`).then((r) => (r.ok ? r.json() : null)),
        ]);
        if (!alive) return;
        if (!health) {
          setStats({ online: false, agents: null, tools: null, approvalsPending: null, providers: [] });
          return;
        }
        setStats({
          online: true,
          tools: typeof health.tools_available === "number" ? health.tools_available : null,
          agents: Array.isArray(team) ? team.length : null,
          approvalsPending: Array.isArray(pending) ? pending.length : null,
          providers: Array.isArray(gw?.preferred_order) ? gw.preferred_order : [],
        });
      } catch {
        if (alive)
          setStats({ online: false, agents: null, tools: null, approvalsPending: null, providers: [] });
      }
    };
    load();
    const t = setInterval(load, intervalMs);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [intervalMs]);

  return stats;
}
