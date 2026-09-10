import { useEffect, useState } from "react";
import { API_URL } from "@/config";
import { PageHeader } from "@/components/Layout/PageHeader";
import { useCommandStats } from "@/hooks/useCommandStats";
import { useTranslation } from "react-i18next";

function fmt(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : String(v);
}

function Section({ title, right, children }: { title: string; right?: string; children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl border"
      style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
    >
      <div
        className="flex items-center justify-between px-3 py-2 border-b"
        style={{ borderColor: "var(--border-glass)" }}
      >
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

function TR({ cells, mono = false }: { cells: React.ReactNode[]; mono?: boolean }) {
  return (
    <tr className="border-b last:border-0" style={{ borderColor: "var(--border-glass)" }}>
      {cells.map((c, i) => (
        <td
          key={i}
          className={`px-3 py-2 text-xs ${mono ? "mono" : ""} ${i === 0 ? "font-medium" : ""}`}
          style={{ color: i === 0 ? "var(--text-0)" : "var(--text-1)" }}
        >
          {c}
        </td>
      ))}
    </tr>
  );
}

function TH({ labels }: { labels: string[] }) {
  return (
    <tr className="border-b" style={{ borderColor: "var(--border-glass)" }}>
      {labels.map((l) => (
        <th
          key={l}
          className="px-3 py-1.5 text-left text-[10px] font-semibold tracking-wider"
          style={{ color: "var(--text-2)" }}
        >
          {l.toUpperCase()}
        </th>
      ))}
    </tr>
  );
}

export function CommandCenter({ onNavigate }: { onNavigate: (id: string) => void }) {
  const { t } = useTranslation();
  const s = useCommandStats();
  const [busy, setBusy] = useState<string | null>(null);

  const act = async (url: string, opts: RequestInit, key: string) => {
    setBusy(key);
    try {
      await fetch(url, opts);
    } catch {
      /* status refresh on next poll surfaces failures */
    } finally {
      setBusy(null);
    }
  };

  const approveDeferred = (id: string) =>
    act(
      `${API_URL}/api/v1/memory/deferred/${id}/resolve?status=approved`,
      { method: "POST" },
      `df-${id}`,
    );

  const btn =
    "text-[11px] font-semibold px-2 py-1 rounded-md border transition-colors disabled:opacity-40";

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="max-w-6xl mx-auto space-y-3">
        <PageHeader
          title={t("ops.title")}
          description={
            s.online
              ? t("ops.subtitle_live")
              : t("ops.subtitle_offline")
          }
        />

        {!s.online && (
          <div
            className="rounded-xl border px-3 py-2 text-xs"
            style={{
              background: "rgba(248,113,113,0.06)",
              borderColor: "rgba(248,113,113,0.25)",
              color: "#f87171",
            }}
          >
            {t("ops.offline_banner")}
          </div>
        )}

        {/* Providers */}
        <Section title={t("ops.providers")} right={s.online ? `${s.providers.length} live` : undefined}>
          <table className="w-full">
            <thead>
              <TH labels={["provider", "models", "req/min", "fail streak", "cost $", "state"]} />
            </thead>
            <tbody>
              {s.providers.length === 0 && (
                <TR cells={[<span key="e">{s.online ? t("ops.no_providers") : "—"}</span>]} />
              )}
              {s.providers.map((p) => {
                const rl = s.rateLimits[p];
                const blocked = !!rl?.blocked;
                return (
                  <TR
                    key={p}
                    mono
                    cells={[
                      p,
                      (s.providerModels[p] || []).slice(0, 2).join(", ") || "—",
                      rl ? `${rl.requests_this_minute}/${rl.max_per_minute}` : "—",
                      fmt(rl?.consecutive_failures),
                      (s.costs[p] ?? 0).toFixed(4),
                      <span
                        key="st"
                        className="inline-flex items-center gap-1.5"
                        style={{ color: !s.online ? "#f87171" : blocked ? "#f5a524" : "#34d399" }}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full"
                          style={{
                            background: !s.online ? "#f87171" : blocked ? "#f5a524" : "#34d399",
                          }}
                        />
                        {!s.online ? "down" : blocked ? "limited" : "ok"}
                      </span>,
                    ]}
                  />
                );
              })}
            </tbody>
          </table>
        </Section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Approvals */}
          <Section
            title={t("ops.approvals")}
            right={s.online ? `${s.approvalsPending ?? 0} pending` : undefined}
          >
            <table className="w-full">
              <thead>
                <TH labels={["request", "risk", "action"]} />
              </thead>
            <tbody>
              <ApprovalRows btn={btn} emptyLabel={s.online ? t("ops.queue_clear") : "—"} />
            </tbody>
            </table>
          </Section>

          {/* Deferred */}
          <Section
            title={t("ops.deferred")}
            right={s.online ? `${s.deferred.length} queued` : undefined}
          >
            <table className="w-full">
              <thead>
                <TH labels={["task", "model", "action"]} />
              </thead>
              <tbody>
                {s.deferred.length === 0 && (
                  <TR cells={[<span key="e">{s.online ? t("ops.queue_clear") : "—"}</span>]} />
                )}
                {s.deferred.slice(0, 5).map((d) => (
                  <TR
                    key={d.id}
                    cells={[
                      <span key="t" title={d.reason}>
                        {d.id.slice(0, 8)} · {(d.reason || "").slice(0, 42)}
                      </span>,
                      <span key="m" className="mono">{d.model}</span>,
                      <button
                        key="b"
                        disabled={busy === `df-${d.id}`}
                        onClick={() => approveDeferred(d.id)}
                        className={btn}
                        style={{
                          borderColor: "rgba(52,211,153,0.4)",
                          color: "#34d399",
                          background: "rgba(52,211,153,0.08)",
                        }}
                      >
                        {t("ops.assign")}
                      </button>,
                    ]}
                  />
                ))}
              </tbody>
            </table>
          </Section>
        </div>

        {/* Recent routes */}
        <Section title={t("ops.routes")} right={s.online ? `${s.chains.length} recent` : undefined}>
          <table className="w-full">
            <thead>
              <TH labels={["final", "result", "model", "latency ms", "path"]} />
            </thead>
            <tbody>
              {s.chains.length === 0 && (
                <TR cells={[<span key="e">{s.online ? t("ops.no_routes") : "—"}</span>]} />
              )}
              {s.chains.slice(0, 5).map((c, i) => (
                <TR
                  key={i}
                  mono
                  cells={[
                    c.final_provider ?? "?",
                    <span key="r" style={{ color: c.final_success ? "#34d399" : "#f87171" }}>
                      {c.final_success ? "ok" : "fail"}
                    </span>,
                    c.final_model ?? "—",
                    Math.round(c.total_latency_ms).toString(),
                    c.attempts.map((a) => `${a.provider}${a.success ? "" : "✕"}`).join(" → "),
                  ]}
                />
              ))}
            </tbody>
          </table>
        </Section>

        <div className="flex gap-2">
          <button
            onClick={() => onNavigate("chat")}
            className="text-xs font-semibold px-3 py-2 rounded-lg text-white"
            style={{ background: "var(--accent)" }}
          >
            {t("ops.open_chat")}
          </button>
          <button
            onClick={() => onNavigate("approvals")}
            className="text-xs font-semibold px-3 py-2 rounded-lg border"
            style={{ borderColor: "var(--border-glass)", color: "var(--text-1)" }}
          >
            {t("ops.open_approvals")}
          </button>
        </div>
      </div>
    </div>
  );
}

function ApprovalRows({
  btn,
  emptyLabel,
}: {
  btn: string;
  emptyLabel: string;
}) {
  const [rows, setRows] = useState<any[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`${API_URL}/api/v1/approvals/pending`)
      .then((r) => (r.ok ? r.json() : []))
      .then((j) => {
        if (alive) setRows(Array.isArray(j) ? j.slice(0, 5) : []);
      })
      .catch(() => {
        if (alive) setRows([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  const resolve = async (id: string, ok: boolean) => {
    const key = `${id}-${ok}`;
    setBusy(key);
    try {
      const r = await fetch(`${API_URL}/api/v1/approvals/${id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: ok ? "approved" : "rejected", decided_by: "human" }),
      });
      if (r.ok) setRows((prev) => (prev || []).filter((x) => (x.request_id || x.id) !== id));
    } catch {
      /* badge refresh on next poll surfaces failures */
    } finally {
      setBusy(null);
    }
  };

  if (rows === null) return <TR cells={[<span key="l">…</span>]} />;
  if (rows.length === 0) return <TR cells={[<span key="e">{emptyLabel}</span>]} />;
  return (
    <>
      {rows.map((r) => {
        const id = r.request_id || r.id;
        return (
          <TR
            key={id}
            cells={[
              <span key="t" title={r.action_description || r.action || ""}>
                {(r.tool_name ? `${r.tool_name} · ` : "") +
                  (r.action_description || r.action || id || "").slice(0, 40)}
              </span>,
              <span
                key="r"
                className="mono"
                style={{
                  color: (r.risk_score ?? 0) >= 70 ? "#f87171" : (r.risk_score ?? 0) >= 40 ? "#f5a524" : "#34d399",
                }}
              >
                {r.risk || r.risk_score || "—"}
              </span>,
              <span key="b" className="flex gap-1.5">
                <button
                  disabled={busy === `${id}-true`}
                  onClick={() => resolve(id, true)}
                  className={btn}
                  style={{
                    borderColor: "rgba(52,211,153,0.4)",
                    color: "#34d399",
                    background: "rgba(52,211,153,0.08)",
                  }}
                >
                  ✓
                </button>
                <button
                  disabled={busy === `${id}-false`}
                  onClick={() => resolve(id, false)}
                  className={btn}
                  style={{
                    borderColor: "rgba(248,113,113,0.4)",
                    color: "#f87171",
                    background: "rgba(248,113,113,0.08)",
                  }}
                >
                  ✕
                </button>
              </span>,
            ]}
          />
        );
      })}
    </>
  );
}
