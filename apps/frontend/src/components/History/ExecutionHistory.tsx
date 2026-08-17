import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, Clock, ChevronRight, ChevronDown, Filter } from "lucide-react";

interface Execution {
  id: string;
  workflow_name: string;
  status: "completed" | "failed" | "running" | "cancelled";
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  trigger: string;
  steps: { name: string; status: string; duration_ms: number }[];
  error?: string;
}

const DEMO_DATA: Execution[] = [
  {
    id: "exec-1",
    workflow_name: "Lead Processing Pipeline",
    status: "completed",
    started_at: "2026-08-16T14:30:00Z",
    completed_at: "2026-08-16T14:32:15Z",
    duration_ms: 135000,
    trigger: "Webhook (HubSpot)",
    steps: [
      { name: "Fetch new leads", status: "completed", duration_ms: 2000 },
      { name: "Score leads", status: "completed", duration_ms: 5000 },
      { name: "Create Slack notification", status: "completed", duration_ms: 1500 },
      { name: "Update CRM", status: "completed", duration_ms: 3000 },
    ],
  },
  {
    id: "exec-2",
    workflow_name: "Code Review Auto-Approver",
    status: "failed",
    started_at: "2026-08-16T12:00:00Z",
    completed_at: "2026-08-16T12:00:45Z",
    duration_ms: 45000,
    trigger: "Manual",
    steps: [
      { name: "Clone repository", status: "completed", duration_ms: 5000 },
      { name: "Run linter", status: "completed", duration_ms: 8000 },
      { name: "Run tests", status: "failed", duration_ms: 30000 },
    ],
    error: "Test suite failed: 3/47 tests failed in test_auth.py",
  },
  {
    id: "exec-3",
    workflow_name: "Daily Standup Report",
    status: "completed",
    started_at: "2026-08-16T09:00:00Z",
    completed_at: "2026-08-16T09:01:30Z",
    duration_ms: 90000,
    trigger: "Cron (daily 9:00)",
    steps: [
      { name: "Collect team updates", status: "completed", duration_ms: 30000 },
      { name: "Generate summary", status: "completed", duration_ms: 40000 },
      { name: "Post to Slack #standup", status: "completed", duration_ms: 2000 },
    ],
  },
];

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "completed": return <CheckCircle className="w-4 h-4 text-green-400" />;
    case "failed": return <XCircle className="w-4 h-4 text-red-400" />;
    case "running": return <Clock className="w-4 h-4 text-yellow-400 animate-spin" />;
    default: return <Clock className="w-4 h-4 text-gray-400" />;
  }
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-500/10 text-green-300 border-green-500/20",
    failed: "bg-red-500/10 text-red-300 border-red-500/20",
    running: "bg-yellow-500/10 text-yellow-300 border-yellow-500/20",
    cancelled: "bg-gray-500/10 text-gray-300 border-gray-500/20",
  };
  return <Badge className={colors[status] || colors.cancelled}>{status.toUpperCase()}</Badge>;
}

function formatDuration(ms?: number) {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export function ExecutionHistory() {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Execution History</h2>
        <div className="flex gap-2">
          <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-600 text-gray-300 text-sm hover:bg-white/5">
            <Filter className="w-3 h-3" /> Filter
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {DEMO_DATA.map((exec) => (
          <div key={exec.id} className="glass-card overflow-hidden">
            <button
              onClick={() => setExpandedId(expandedId === exec.id ? null : exec.id)}
              className="w-full p-4 flex items-center gap-4 text-left hover:bg-white/5 transition-colors"
            >
              <StatusIcon status={exec.status} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium truncate">{exec.workflow_name}</span>
                  <StatusBadge status={exec.status} />
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>{new Date(exec.started_at).toLocaleString()}</span>
                  <span>·</span>
                  <span>{exec.trigger}</span>
                  <span>·</span>
                  <span>{formatDuration(exec.duration_ms)}</span>
                </div>
              </div>
              {expandedId === exec.id ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )}
            </button>

            {expandedId === exec.id && (
              <div className="border-t border-white/5 p-4 space-y-3">
                {exec.steps.map((step, i) => (
                  <div key={i} className="flex items-center gap-3 pl-4">
                    <StatusIcon status={step.status} />
                    <span className="text-gray-300 text-sm flex-1">{step.name}</span>
                    <span className="text-gray-500 text-xs">{formatDuration(step.duration_ms)}</span>
                  </div>
                ))}
                {exec.error && (
                  <div className="mt-3 p-3 rounded-lg bg-red-500/5 border border-red-500/20 text-red-300 text-xs font-mono">
                    {exec.error}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
