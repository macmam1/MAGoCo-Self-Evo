import { useEffect, useState } from "react";
import { TrendingUp, Lightbulb, Clock, Share2, Check, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button, Badge } from "@/components/ui";
import { API_URL } from "@/config";

export function GrowthDashboard() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [s, sg, tl] = await Promise.all([
        fetch(`${API_URL}/api/v1/growth/learning-rate`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_URL}/api/v1/growth/suggestions`).then((r) => (r.ok ? r.json() : [])),
        fetch(`${API_URL}/api/v1/growth/timeline?limit=30`).then((r) => (r.ok ? r.json() : [])),
      ]);
      if (s) setStats(s);
      if (sg) setSuggestions(sg);
      if (tl) setTimeline(tl);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const act = async (id: string, action: string) => {
    await fetch(`${API_URL}/api/v1/growth/suggestions/${id}/${action}`, { method: "POST" });
    load();
  };

  const runDemo = async () => {
    const seq = ["chat:send", "browser:navigate", "browser:screenshot"];
    for (let i = 0; i < 4; i++) {
      for (const s of seq) {
        const [action, target] = s.split(":");
        await fetch(`${API_URL}/api/v1/growth/record`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agent_id: "default", action, target, session_id: "demo" }),
        });
      }
    }
    await fetch(`${API_URL}/api/v1/growth/suggest`, { method: "POST" });
    load();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
            <TrendingUp className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="font-medium text-sm text-white">{t("growth.title", "Agent Growth")}</h2>
            <p className="text-xs text-text-2">{t("growth.subtitle", "Patterns, auto-skills, timeline")}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={runDemo} disabled={loading}>Demo pattern</Button>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>Refresh</Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[["Events", stats.total_events], ["Suggestions", stats.suggestions], ["Applied", stats.applied], ["Conversion", `${Math.round((stats.conversion || 0) * 100)}%`]].map(([k, v]) => (
              <div key={k as string} className="p-4 rounded-xl border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                <div className="text-[11px] text-text-2">{k}</div>
                <div className="text-2xl font-bold">{String(v)}</div>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div className="p-4 rounded-xl border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
            <h3 className="font-medium mb-3 flex items-center gap-2"><Lightbulb className="h-4 w-4" />Suggestions ({suggestions.length})</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {suggestions.map((s: any) => (
                <div key={s.id} className="p-3 rounded-lg border" style={{ borderColor: "var(--border-glass)", background: "var(--bg-2)" }}>
                  <div className="text-sm font-medium">{s.title}</div>
                  <div className="text-xs text-text-2 mt-1 line-clamp-2">{s.description}</div>
                  <div className="flex gap-2 mt-2">
                    <Badge variant="outline" className="text-[10px]">{s.status}</Badge>
                    {s.status === "pending" && (
                      <>
                        <button onClick={() => act(s.id, "approved")} className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-300 flex items-center gap-1"><Check className="h-3 w-3" />Approve</button>
                        <button onClick={() => act(s.id, "rejected")} className="text-xs px-2 py-1 rounded bg-red-500/10 text-red-300 flex items-center gap-1"><X className="h-3 w-3" />Reject</button>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {suggestions.length === 0 && <p className="text-xs text-text-2">No suggestions yet — run demo.</p>}
            </div>
          </div>

          <div className="p-4 rounded-xl border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
            <h3 className="font-medium mb-3 flex items-center gap-2"><Clock className="h-4 w-4" />Timeline</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {timeline.map((e: any) => (
                <div key={e.id} className="text-xs border-l-2 pl-3" style={{ borderColor: "var(--accent)" }}>
                  <div className="font-medium">{e.title}</div>
                  <div className="text-text-2">{e.type} · {new Date(e.created_at).toLocaleString()}</div>
                </div>
              ))}
              {timeline.length === 0 && <p className="text-xs text-text-2">Empty.</p>}
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl border flex items-center justify-between" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
          <div className="text-sm flex items-center gap-2"><Share2 className="h-4 w-4" />Cross-agent memory sharing</div>
          <ShareBox onDone={load} />
        </div>
      </div>
    </div>
  );
}

function ShareBox({ onDone }: { onDone: () => void }) {
  const [from, setFrom] = useState("default");
  const [to, setTo] = useState("agent2");
  const share = async () => {
    await fetch(`${API_URL}/api/v1/growth/share`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_agent: from, to_agent: to, memory_ids: [] }),
    });
    onDone();
  };
  return (
    <div className="flex gap-2">
      <input value={from} onChange={(e) => setFrom(e.target.value)} className="w-24 bg-gray-800/50 border border-white/10 rounded px-2 py-1 text-xs" />
      <span className="text-xs">→</span>
      <input value={to} onChange={(e) => setTo(e.target.value)} className="w-24 bg-gray-800/50 border border-white/10 rounded px-2 py-1 text-xs" />
      <Button size="sm" onClick={share}>Share</Button>
    </div>
  );
}
