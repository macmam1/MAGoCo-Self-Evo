import { useEffect, useState } from "react";
import { API_URL } from "@/config";

export interface FallbackChain {
  final_provider: string | null;
  final_success: boolean;
  final_model: string | null;
  total_latency_ms: number;
  attempts: { provider: string; success: boolean; error: string | null }[];
}

export interface CommandStats {
  online: boolean;
  agents: number | null;
  tools: number | null;
  approvalsPending: number | null;
  providers: string[];
  rateLimits: Record<string, {
    requests_this_minute: number;
    max_per_minute: number;
    consecutive_failures: number;
    blocked: boolean;
    total_requests: number;
  }>;
  costs: Record<string, number>;
  providerModels: Record<string, string[]>;
  deferred: { id: string; model: string; reason: string }[];
  chains: FallbackChain[];
}

/** Live command-center stats. null = unknown (offline/loading) — never mock numbers. */
export function useCommandStats(intervalMs = 30000) {
  const [stats, setStats] = useState<CommandStats>({
    online: false,
    agents: null,
    tools: null,
    approvalsPending: null,
    providers: [],
    rateLimits: {},
    costs: {},
    providerModels: {},
    deferred: [],
    chains: [],
  });

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [health, team, pending, gw, reg, deferred, chains] = await Promise.all([
          fetch(`${API_URL}/health`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/planning/team`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/approvals/pending`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/providers/gateway/status`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/providers/`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/memory/deferred`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_URL}/api/v1/providers/gateway/fallbacks?limit=5`).then((r) => (r.ok ? r.json() : null)),
        ]);
        if (!alive) return;
        if (!health) {
          setStats({
            online: false, agents: null, tools: null, approvalsPending: null,
            providers: [], rateLimits: {}, costs: {}, providerModels: {}, deferred: [], chains: [],
          });
          return;
        }
        const models: Record<string, string[]> = {};
        if (Array.isArray(reg)) for (const p of reg) models[p.id] = p.models || [];
        setStats({
          online: true,
          tools: typeof health.tools_available === "number" ? health.tools_available : null,
          agents: Array.isArray(team) ? team.length : null,
          approvalsPending: Array.isArray(pending) ? pending.length : null,
          providers: Array.isArray(gw?.preferred_order) ? gw.preferred_order : [],
          rateLimits: gw?.rate_limits || {},
          costs: gw?.costs || {},
          providerModels: models,
          deferred: Array.isArray(deferred) ? deferred : [],
          chains: Array.isArray(chains) ? chains : [],
        });
      } catch {
        if (alive)
          setStats({
            online: false, agents: null, tools: null, approvalsPending: null,
            providers: [], rateLimits: {}, costs: {}, providerModels: {}, deferred: [], chains: [],
          });
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
