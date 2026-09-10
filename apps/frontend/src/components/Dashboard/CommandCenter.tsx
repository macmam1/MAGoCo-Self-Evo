import { ArrowRight, Bot, Play, History, Workflow as WorkflowIcon, Globe } from "lucide-react";
import { PageHeader } from "@/components/Layout/PageHeader";
import { useCommandStats } from "@/hooks/useCommandStats";

const QUICK = [
  {
    id: "chat",
    title: "Ask an agent",
    desc: "Chat with ReAct + streaming + tool calls",
    icon: Bot,
  },
  {
    id: "browser",
    title: "Agent Browser",
    desc: "Live browser sessions with AI control",
    icon: Globe,
  },
  {
    id: "workflows",
    title: "Run a workflow",
    desc: "Execute a DAG on the real engine",
    icon: WorkflowIcon,
  },
  {
    id: "history",
    title: "Review runs",
    desc: "Audit trail of every execution",
    icon: History,
  },
];

function fmt(v: number | null): string {
  return v === null ? "—" : String(v);
}

export function CommandCenter({ onNavigate }: { onNavigate: (id: string) => void }) {
  const s = useCommandStats();
  const providerCount = s.online ? s.providers.length : null;

  const STATS = [
    {
      label: "Agents on roster",
      value: fmt(s.agents),
      sub: s.online ? "named specialists" : "backend offline",
      tint: "#7c5cff",
    },
    {
      label: "Tools registered",
      value: fmt(s.tools),
      sub: s.online ? "guarded + audited" : "backend offline",
      tint: "#22d3ee",
    },
    {
      label: "Approvals pending",
      value: fmt(s.approvalsPending),
      sub:
        s.approvalsPending === null
          ? "backend offline"
          : s.approvalsPending > 0
            ? "needs your sign-off"
            : "queue clear",
      tint: "#f5a524",
    },
    {
      label: "Providers live",
      value: fmt(providerCount),
      sub:
        providerCount === null
          ? "backend offline"
          : providerCount > 0
            ? s.providers.slice(0, 3).join(" · ") + (s.providers.length > 3 ? "…" : "")
            : "none configured",
      tint: "#34d399",
    },
  ];

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <PageHeader
          title="Command Center"
          description={
            s.online
              ? "Live system state — every number below comes from the running backend."
              : "Backend offline — showing last known structure, no live data."
          }
        />

        {/* Stats — all live, never mocked */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {STATS.map((st) => (
            <div
              key={st.label}
              className="rounded-2xl border p-4"
              style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
            >
              <div className="text-[11px] font-medium" style={{ color: "var(--text-2)" }}>
                {st.label}
              </div>
              <div className="text-2xl font-bold mt-1 mono" style={{ color: st.tint }}>
                {st.value}
              </div>
              <div className="text-[11px] mt-0.5 truncate" style={{ color: "var(--text-2)" }}>
                {st.sub}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Quick launch */}
          <div
            className="rounded-2xl border p-4"
            style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
          >
            <div className="text-sm font-semibold mb-3" style={{ color: "var(--text-0)" }}>
              Quick launch
            </div>
            <div className="space-y-2">
              {QUICK.map((q) => (
                <button
                  key={q.id}
                  onClick={() => onNavigate(q.id)}
                  className="w-full flex items-center gap-3 rounded-xl border p-3 text-left transition-colors hover:border-[var(--accent)]"
                  style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}
                >
                  <q.icon className="h-4 w-4 shrink-0" style={{ color: "var(--accent)" }} />
                  <span className="flex-1">
                    <span className="block text-[13px] font-medium" style={{ color: "var(--text-0)" }}>
                      {q.title}
                    </span>
                    <span className="block text-[11px]" style={{ color: "var(--text-2)" }}>
                      {q.desc}
                    </span>
                  </span>
                  <ArrowRight className="h-4 w-4" style={{ color: "var(--text-2)" }} />
                </button>
              ))}
            </div>
          </div>

          {/* System status — live only */}
          <div
            className="rounded-2xl border p-4"
            style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
          >
            <div className="text-sm font-semibold mb-3" style={{ color: "var(--text-0)" }}>
              System status
            </div>
            <div className="space-y-2.5 text-[13px]" style={{ color: "var(--text-1)" }}>
              <Row ok={s.online} label="Backend API" />
              <Row
                ok={s.online && s.providers.length > 0}
                label={
                  !s.online
                    ? "LLM providers (unknown — offline)"
                    : s.providers.length > 0
                      ? `LLM providers (${s.providers.length} live)`
                      : "LLM providers (none configured)"
                }
              />
              <Row
                ok={s.online && (s.approvalsPending ?? 1) === 0}
                warn={s.online && (s.approvalsPending ?? 0) > 0}
                label={
                  !s.online
                    ? "Approvals queue (unknown — offline)"
                    : `Approvals queue (${s.approvalsPending ?? 0} pending)`
                }
              />
              <button
                onClick={() => onNavigate("chat")}
                className="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold rounded-lg px-3 py-2 text-white"
                style={{ background: "var(--accent)" }}
              >
                <Play className="h-3.5 w-3.5" /> Open Agent Chat
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ ok, label, warn }: { ok: boolean; label: string; warn?: boolean }) {
  const color = ok ? "#34d399" : warn ? "#f5a524" : "#f87171";
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
      <span>{label}</span>
    </div>
  );
}
