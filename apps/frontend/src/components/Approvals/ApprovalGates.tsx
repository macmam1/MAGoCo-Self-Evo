import { useState, useEffect, useCallback } from "react";
import { CheckCircle, XCircle, Clock, BookOpen } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ApprovalRequest {
  request_id: string;
  agent_name: string;
  action_description: string;
  proposed_input: Record<string, unknown>;
  status: "pending" | "approved" | "rejected" | "expired" | "skipped";
  created_at: string;
  tool_name?: string;
  action?: string;
  resource?: string;
  risk?: string;
  risk_score?: number;
  expires_at?: string | null;
  decided_by?: string;
}

const RISK_STYLES: Record<string, string> = {
  low: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  medium: "bg-yellow-500/10 text-yellow-300 border-yellow-500/30",
  high: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  critical: "bg-red-500/10 text-red-300 border-red-500/30",
};

export function ApprovalGates() {
  const { i18n, t } = useTranslation();
  const lang = (i18n.language || "en").startsWith("fa") ? "fa" : "en";
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPending = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/approvals/pending");
      if (res.ok) {
        const data = await res.json();
        setRequests(data);
      }
    } catch {
      // Fallback demo data
      setRequests([
        {
          request_id: "demo-1",
          agent_name: "Coder Agent",
          action_description: "Commit code to main branch: 'fix: update login validation'",
          proposed_input: { branch: "main", files: ["src/auth.py"] },
          status: "pending",
          created_at: new Date().toISOString(),
        },
        {
          request_id: "demo-2",
          agent_name: "Researcher Agent",
          action_description: "Send API request to external service: HubSpot CRM",
          proposed_input: { endpoint: "/api/contacts", method: "POST" },
          status: "pending",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPending();
    const t = setInterval(fetchPending, 15000);
    return () => clearInterval(t);
  }, [fetchPending]);

  const handleApproval = async (id: string, status: "approved" | "rejected") => {
    try {
      await fetch(`/api/v1/approvals/${id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
    } catch {
      // Demo mode — just update local state
    }
    setRequests((prev) => prev.map((r) => (r.request_id === id ? { ...r, status } : r)));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-gray-400">Loading approvals...</div>
      </div>
    );
  }

  const pending = requests.filter((r) => r.status === "pending");
  const resolved = requests.filter((r) => r.status !== "pending");

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold text-white">Human-in-the-Loop Approvals</h2>
        {pending.length > 0 && (
          <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/30 animate-pulse">
            {pending.length} pending
          </Badge>
        )}
      </div>

      {pending.length === 0 && (
        <div className="text-center text-gray-500 py-12">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500/50" />
          No pending approvals. All clear!
        </div>
      )}

      {pending.map((req) => (
        <div
          key={req.request_id}
          className="glass-card p-5 border-l-4 border-yellow-500/50 space-y-4"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <Clock className="w-4 h-4 text-yellow-400" />
                <span className="text-sm text-yellow-300 font-medium">
                  {req.agent_name}
                </span>
                <Badge className="bg-yellow-500/10 text-yellow-300 text-xs">PENDING</Badge>
                {req.risk && (
                  <Badge className={`text-xs border ${RISK_STYLES[req.risk] || RISK_STYLES.medium}`}>
                    RISK: {req.risk.toUpperCase()}{typeof req.risk_score === "number" ? ` ${req.risk_score}` : ""}
                  </Badge>
                )}
                {req.tool_name && (
                  <Badge className="bg-white/5 text-gray-300 text-xs font-mono">{req.tool_name}</Badge>
                )}
              </div>
              <p className="text-white font-medium">{req.action_description}</p>
              {req.expires_at && (
                <p className="text-gray-500 text-xs mt-1">Expires: {new Date(req.expires_at).toLocaleString()}</p>
              )}
            </div>
          </div>

          {(() => {
            const expl = (req.proposed_input as any)?.explanation;
            const e = expl?.[lang] || expl?.en;
            const purpose = expl?.model_purpose;
            if (!e && !purpose) return null;
            return (
              <div className="rounded-lg p-3 text-xs space-y-1 border border-sky-500/20 bg-sky-500/5">
                <div className="flex items-center gap-1.5 text-sky-300 font-medium">
                  <BookOpen className="w-3.5 h-3.5" />
                  {t("approvals.what_is_this", "What is this?")}
                </div>
                {e && (
                  <>
                    <p className="text-white">{e.summary}</p>
                    <p className="text-gray-400">{e.details}</p>
                    <p className={e.reversible ? "text-emerald-300" : "text-orange-300"}>
                      {e.reversible
                        ? t("approvals.reversible", "Reversible — safe to approve.")
                        : t("approvals.irreversible", "Not automatically reversible — approve only if you understand it.")}
                    </p>
                  </>
                )}
                {purpose && (
                  <p className="text-gray-300 italic">
                    {t("approvals.agent_why", "Agent's reason:")} {purpose}
                  </p>
                )}
              </div>
            );
          })()}

          <details className="bg-black/30 rounded-lg p-3 text-xs font-mono text-gray-300">
            <summary className="cursor-pointer text-gray-500">{t("approvals.raw_details", "Raw details")}</summary>
            <pre className="mt-2">{JSON.stringify(req.proposed_input, null, 2)}</pre>
          </details>

          <div className="flex gap-3">
            <Button
              onClick={() => handleApproval(req.request_id, "approved")}
              className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" /> Approve
            </Button>
            <Button
              onClick={() => handleApproval(req.request_id, "rejected")}
              variant="destructive"
              className="flex items-center gap-2"
            >
              <XCircle className="w-4 h-4" /> Reject
            </Button>
          </div>
        </div>
      ))}

      {resolved.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Resolved</h3>
          {resolved.map((req) => (
            <div
              key={req.request_id}
              className="glass-card p-4 opacity-60 flex items-center gap-3"
            >
              {req.status === "approved" ? (
                <CheckCircle className="w-5 h-5 text-green-400" />
              ) : (
                <XCircle className="w-5 h-5 text-red-400" />
              )}
              <div className="flex-1">
                <p className="text-white text-sm">{req.action_description}</p>
                <p className="text-gray-500 text-xs">{req.agent_name}</p>
              </div>
              <Badge
                className={
                  req.status === "approved"
                    ? "bg-green-500/10 text-green-300"
                    : "bg-red-500/10 text-red-300"
                }
              >
                {req.status.toUpperCase()}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
