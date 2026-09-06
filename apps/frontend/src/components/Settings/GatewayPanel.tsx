import { useEffect, useState, useCallback } from "react";
import { RefreshCw, DollarSign, Gauge, GitBranch } from "lucide-react";
import { API_URL } from "@/config";
import { cn } from "@/lib/utils";

interface GatewayStatus {
  providers: string[];
  preferred_order: string[];
  costs: Record<string, number>;
  rate_limits: Record<string, {
    requests_this_minute: number;
    max_per_minute: number;
    total_requests: number;
    total_tokens: number;
    consecutive_failures: number;
    blocked: boolean;
  }>;
  models: string[];
}

interface FallbackChain {
  original_provider: string;
  original_model: string;
  final_success: boolean;
  final_provider: string | null;
  final_model: string | null;
  total_latency_ms: number;
  attempts: { provider: string; model: string; success: boolean; error: string | null; latency_ms: number | null }[];
}

export function GatewayPanel() {
  const [status, setStatus] = useState<GatewayStatus | null>(null);
  const [chains, setChains] = useState<FallbackChain[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, f] = await Promise.all([
        fetch(`${API_URL}/api/v1/providers/gateway/status`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_URL}/api/v1/providers/gateway/fallbacks?limit=10`).then((r) => (r.ok ? r.json() : [])),
      ]);
      setStatus(s);
      setChains(Array.isArray(f) ? f : []);
    } catch {
      // backend down — show empty state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, 30000);
    return () => clearInterval(t);
  }, [fetchAll]);

  const totalCost = status ? Object.values(status.costs || {}).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-text-2">Session spend</span>
          <span className="font-semibold text-text-0">${totalCost.toFixed(4)}</span>
        </div>
        <button onClick={fetchAll} disabled={loading} className="p-1.5 rounded-lg hover:bg-white/5">
          <RefreshCw className={cn("h-3.5 w-3.5 text-text-2", loading && "animate-spin")} />
        </button>
      </div>

      {!status && !loading && (
        <p className="text-[11px] text-text-2">Gateway offline — start the backend to see live costs.</p>
      )}

      {status && Object.keys(status.rate_limits || {}).map((name) => {
        const rl = status.rate_limits[name];
        const pct = Math.min(100, (rl.requests_this_minute / Math.max(1, rl.max_per_minute)) * 100);
        return (
          <div key={name} className="p-2.5 bg-white/5 rounded-xl border border-white/5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-text-0">{name}</span>
              <span className={cn(
                "text-[10px] px-1.5 py-0.5 rounded-full border",
                rl.blocked
                  ? "bg-red-500/10 text-red-300 border-red-500/20"
                  : rl.consecutive_failures > 0
                    ? "bg-orange-500/10 text-orange-300 border-orange-500/20"
                    : "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
              )}>
                {rl.blocked ? "RATE-LIMITED" : rl.consecutive_failures > 0 ? `${rl.consecutive_failures} fails` : "healthy"}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1.5">
              <Gauge className="h-3 w-3 text-text-2" />
              <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full rounded-full bg-primary-500 transition-all" style={{ width: `${pct}%` }} />
              </div>
              <span className="text-[10px] text-text-2">{rl.requests_this_minute}/{rl.max_per_minute} rpm</span>
            </div>
            <div className="text-[10px] text-text-2 mt-1">
              ${(status.costs?.[name] || 0).toFixed(4)} · {rl.total_requests} req · {(rl.total_tokens || 0).toLocaleString()} tok
            </div>
          </div>
        );
      })}

      {chains.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-text-1">
            <GitBranch className="h-3.5 w-3.5" /> Recent fallbacks
          </div>
          {chains.slice(0, 5).map((c, i) => (
            <div key={i} className="text-[11px] p-2 bg-white/5 rounded-lg border border-white/5 text-text-2">
              <span className={c.final_success ? "text-emerald-300" : "text-red-300"}>
                {c.final_success ? "✓" : "✗"}
              </span>{" "}
              {c.original_provider}:{c.original_model || "auto"}
              {c.final_provider && c.final_provider !== c.original_provider && (
                <span> → {c.final_provider}:{c.final_model}</span>
              )}
              <span className="text-text-2"> · {c.attempts.length} attempt(s) · {Math.round(c.total_latency_ms)}ms</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
