import { ArrowRight, Bot, Play, History, Workflow as WorkflowIcon } from "lucide-react";
import { PageHeader } from "@/components/Layout/PageHeader";
import { useBackendStatus } from "@/hooks/useBackendStatus";

const STATS = [
  { label: "Agents ready", value: "5", sub: "Coordinator · Coder · Reviewer…", tint: "#7c5cff" },
  { label: "Tools registered", value: "7", sub: "guarded + audited", tint: "#22d3ee" },
  { label: "Approvals pending", value: "3", sub: "needs your sign-off", tint: "#f5a524" },
  { label: "Runs today", value: "12", sub: "all green", tint: "#34d399" },
];

const QUICK = [
  {
    id: "chat",
    title: "Ask an agent",
    desc: "Chat with ReAct + streaming + tool calls",
    icon: Bot,
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

export function CommandCenter({ onNavigate }: { onNavigate: (id: string) => void }) {
  const backend = useBackendStatus();

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <PageHeader
          title="Good evening, Operator 👋"
          description="Your multi-agent command center — agents, workflows and tools in one place."
        />

        {/* Stats (Finley pattern) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {STATS.map((s) => (
            <div
              key={s.label}
              className="rounded-2xl border p-4"
              style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
            >
              <div className="text-[11px] font-medium" style={{ color: "var(--text-2)" }}>
                {s.label}
              </div>
              <div className="text-2xl font-bold mt-1" style={{ color: s.tint }}>
                {s.label === "Tools registered" && backend.tools ? backend.tools : s.value}
              </div>
              <div className="text-[11px] mt-0.5" style={{ color: "var(--text-2)" }}>
                {s.sub}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* Quick launch (NeuroNest pattern) */}
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

          {/* System status */}
          <div
            className="rounded-2xl border p-4"
            style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
          >
            <div className="text-sm font-semibold mb-3" style={{ color: "var(--text-0)" }}>
              System status
            </div>
            <div className="space-y-2.5 text-[13px]" style={{ color: "var(--text-1)" }}>
              <Row
                ok={backend.online}
                label={`Backend ${backend.version ? `v${backend.version}` : ""}`}
              />
              <Row ok label="Permission engine + hooks" />
              <Row ok={backend.online} label="WebSocket chat" />
              <Row ok={false} label="LLM provider (mock — connect 9Router)" warn />
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
