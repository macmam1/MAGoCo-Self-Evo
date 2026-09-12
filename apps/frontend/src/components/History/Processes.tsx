import { useCallback, useEffect, useState } from "react";
import { API_URL } from "@/config";
import { PageHeader } from "@/components/Layout/PageHeader";
import { useTranslation } from "react-i18next";

function Section({ title, right, children }: { title: string; right?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border glass" style={{ borderColor: "var(--border-glass)" }}>
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: "var(--border-glass)" }}>
        <span className="text-xs font-semibold tracking-wide" style={{ color: "var(--text-1)" }}>
          {title.toUpperCase()}
        </span>
        {right && (
          <span className="text-[11px] mono" style={{ color: "var(--text-2)" }}>
            {right}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function TH({ labels }: { labels: string[] }) {
  return (
    <tr className="border-b" style={{ borderColor: "var(--border-glass)" }}>
      {labels.map((l) => (
        <th key={l} className="px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider" style={{ color: "var(--text-2)" }}>
          {l.toUpperCase()}
        </th>
      ))}
    </tr>
  );
}

function TR({ cells, mono = false }: { cells: React.ReactNode[]; mono?: boolean }) {
  return (
    <tr className="border-b last:border-0" style={{ borderColor: "var(--border-glass)" }}>
      {cells.map((c, i) => (
        <td key={i} className={`px-3 py-2 text-xs ${mono ? "mono" : ""} ${i === 0 ? "font-medium" : ""}`}
          style={{ color: i === 0 ? "var(--text-0)" : "var(--text-1)" }}>
          {c}
        </td>
      ))}
    </tr>
  );
}

function statusColor(s: string): string {
  const v = (s || "").toLowerCase();
  if (["running", "idle", "loading", "enabled", "ok"].includes(v)) return "#34d399";
  if (["paused", "limited", "scheduled"].includes(v)) return "#f5a524";
  return "#f87171";
}

export function Processes() {
  const { t } = useTranslation();
  const [runs, setRuns] = useState<any[]>([]);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [tabs, setTabs] = useState<any[]>([]);
  const [execs, setExecs] = useState<any[]>([]);
  const [online, setOnline] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, s, b, e] = await Promise.all([
        fetch(`${API_URL}/api/v1/agent-tasks/runs?limit=30`).then((x) => (x.ok ? x.json() : [])),
        fetch(`${API_URL}/api/v1/agent-tasks/schedules`).then((x) => (x.ok ? x.json() : [])),
        fetch(`${API_URL}/api/v1/browser/sessions`).then((x) => (x.ok ? x.json() : [])),
        fetch(`${API_URL}/api/v1/executions/`).then((x) => (x.ok ? x.json() : [])),
      ]);
      setRuns(Array.isArray(r) ? r : []);
      setSchedules(Array.isArray(s) ? s : []);
      setTabs(Array.isArray(b) ? b : []);
      setExecs(Array.isArray(e) ? e : []);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    load();
    const h = setInterval(load, 10000);
    return () => clearInterval(h);
  }, [load]);

  const act = async (key: string, fn: () => Promise<Response>) => {
    setBusy(key);
    try {
      await fn();
      await load();
    } catch {
      /* refresh surfaces failures */
    } finally {
      setBusy(null);
    }
  };

  const live = [
    ...runs.filter((r) => r.status === "running").map((r) => ({ kind: "agent", id: r.id, label: r.agent_name || r.task || r.id, status: r.status, created: r.created_at })),
    ...tabs.map((b) => ({ kind: "browser", id: b.id, label: `${b.title || "tab"} · ${b.url || ""}`.slice(0, 48), status: b.status, created: null as any })),
  ];

  const btn = "text-[11px] font-semibold px-2 py-1 rounded-md border transition-colors disabled:opacity-40";

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="max-w-6xl mx-auto space-y-3">
        <PageHeader
          title={t("proc.title")}
          description={online ? t("proc.subtitle_live") : t("proc.subtitle_offline")}
        />

        {/* Live processes */}
        <Section title={t("proc.live")} right={online ? `${live.length} running` : undefined}>
          <table className="w-full">
            <thead><TH labels={["process", "kind", "status", "action"]} /></thead>
            <tbody>
              {live.length === 0 && (
                <TR cells={[<span key="e">{online ? t("proc.none_live") : "—"}</span>]} />
              )}
              {live.map((p) => (
                <TR
                  key={`${p.kind}-${p.id}`}
                  mono
                  cells={[
                    <span key="l" title={String(p.id)}>{p.label}</span>,
                    p.kind,
                    <span key="s" style={{ color: statusColor(p.status) }}>{p.status}</span>,
                    p.kind === "agent" ? (
                      <button
                        key="b"
                        disabled={busy === `kill-${p.id}`}
                        onClick={() => act(`kill-${p.id}`, () =>
                          fetch(`${API_URL}/api/v1/agent-tasks/background/${p.id}/cancel`, { method: "POST" }))}
                        className={btn}
                        style={{ borderColor: "rgba(248,113,113,0.4)", color: "#f87171", background: "rgba(248,113,113,0.08)" }}
                      >
                        {t("proc.kill")}
                      </button>
                    ) : (
                      <button
                        key="b"
                        disabled={busy === `close-${p.id}`}
                        onClick={() => act(`close-${p.id}`, () =>
                          fetch(`${API_URL}/api/v1/browser/sessions/${p.id}/close`, { method: "POST" }))}
                        className={btn}
                        style={{ borderColor: "rgba(248,113,113,0.4)", color: "#f87171", background: "rgba(248,113,113,0.08)" }}
                      >
                        {t("proc.close")}
                      </button>
                    ),
                  ]}
                />
              ))}
            </tbody>
          </table>
        </Section>

        {/* Schedules */}
        <Section title={t("proc.schedules")} right={online ? `${schedules.length} total` : undefined}>
          <table className="w-full">
            <thead><TH labels={["schedule", "cron", "state", "action"]} /></thead>
            <tbody>
              {schedules.length === 0 && (
                <TR cells={[<span key="e">{online ? t("proc.none_sched") : "—"}</span>]} />
              )}
              {schedules.map((s) => (
                <TR
                  key={s.id}
                  mono
                  cells={[
                    (s.task || s.id || "").slice(0, 48),
                    s.cron || "—",
                    <span key="s" style={{ color: statusColor(s.enabled ? "enabled" : "paused") }}>
                      {s.enabled ? "enabled" : "paused"}
                    </span>,
                    <button
                      key="b"
                      disabled={busy === `tog-${s.id}`}
                      onClick={() => act(`tog-${s.id}`, () =>
                        fetch(`${API_URL}/api/v1/agent-tasks/schedules/${s.id}?enabled=${!s.enabled}`, { method: "PATCH" }))}
                      className={btn}
                      style={{ borderColor: "var(--border-glass)", color: "var(--text-1)" }}
                    >
                      {s.enabled ? t("proc.pause") : t("proc.resume")}
                    </button>,
                  ]}
                />
              ))}
            </tbody>
          </table>
        </Section>

        {/* History */}
        <Section title={t("proc.history")} right={online ? `${runs.length + execs.length} records` : undefined}>
          <table className="w-full">
            <thead><TH labels={["run", "kind", "status", "finished"]} /></thead>
            <tbody>
              {runs.length + execs.length === 0 && (
                <TR cells={[<span key="e">{online ? t("proc.none_hist") : "—"}</span>]} />
              )}
              {runs.filter((r) => r.status !== "running").slice(0, 15).map((r) => (
                <TR
                  key={`r-${r.id}`}
                  mono
                  cells={[
                    (r.agent_id ? `[${String(r.agent_id).slice(0, 11)}] ` : "") +
                      ((r.agent_name ? `${r.agent_name} · ` : "") + (r.id || "").slice(0, 8)),
                    r.kind || "agent",
                    <span key="s" style={{ color: statusColor(r.status) }}>{r.status}</span>,
                    (r.finished_at || "").slice(0, 16).replace("T", " "),
                  ]}
                />
              ))}
              {execs.slice(0, 15).map((e) => (
                <TR
                  key={`e-${e.id}`}
                  mono
                  cells={[
                    String(e.id).slice(0, 8),
                    "workflow",
                    <span key="s" style={{ color: statusColor(e.status) }}>{e.status}</span>,
                    (e.completed_at || "").slice(0, 16).replace("T", " "),
                  ]}
                />
              ))}
            </tbody>
          </table>
        </Section>
      </div>
    </div>
  );
}
