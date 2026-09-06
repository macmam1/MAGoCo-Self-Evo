import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { API_URL } from "@/config";
import { cn } from "@/lib/utils";

interface Plan {
  id: string;
  name: string;
  description: string;
  layer: "os" | "project";
  project_id?: string | null;
  status: string;
  tasks: Task[];
  progress: {
    total: number;
    completed: number;
    failed: number;
    running: number;
    pending: number;
    percent: number;
  };
}

interface Task {
  id: string;
  name: string;
  description: string;
  agent_role: string;
  tool_requirements: string[];
  dependencies: string[];
  status: string;
  result?: string;
  error?: string;
}

export function PlanningPanel() {
  const { t } = useTranslation();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [newPlanName, setNewPlanName] = useState("");
  const [newPlanGoal, setNewPlanGoal] = useState("");
  const [layerFilter, setLayerFilter] = useState<string>("all");
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [executing, setExecuting] = useState<string | null>(null);
  const [execResult, setExecResult] = useState<any>(null);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (layerFilter !== "all") params.set("layer", layerFilter);
      if (projectFilter.trim()) params.set("project_id", projectFilter.trim());
      const qs = params.toString() ? `?${params.toString()}` : "";
      const r = await fetch(`${API_URL}/api/v1/planning${qs}`);
      if (r.ok) setPlans(await r.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layerFilter]);

  const createPlan = async () => {
    if (!newPlanName || !newPlanGoal) return;
    try {
      const r = await fetch(`${API_URL}/api/v1/planning/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newPlanName,
          description: newPlanGoal,
          layer: layerFilter === "project" ? "project" : "os",
          project_id: projectFilter.trim() || undefined,
        }),
      });
      if (r.ok) {
        fetchPlans();
        setShowCreate(false);
        setNewPlanName("");
        setNewPlanGoal("");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const decomposeGoal = async () => {
    if (!newPlanGoal) return;
    try {
      const r = await fetch(`${API_URL}/api/v1/planning/decompose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          goal: newPlanGoal,
          layer: layerFilter === "project" ? "project" : "os",
          project_id: projectFilter.trim() || undefined,
        }),
      });
      if (r.ok) {
        const plan = await r.json();
        fetchPlans();
        setSelectedPlan(plan);
        setShowCreate(false);
        setNewPlanName("");
        setNewPlanGoal("");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deletePlan = async (id: string) => {
    try {
      await fetch(`${API_URL}/api/v1/planning/${id}`, { method: "DELETE" });
      if (selectedPlan?.id === id) setSelectedPlan(null);
      fetchPlans();
    } catch (e) {
      console.error(e);
    }
  };

  const viewPlan = async (id: string) => {
    try {
      const r = await fetch(`${API_URL}/api/v1/planning/${id}`);
      if (r.ok) setSelectedPlan(await r.json());
    } catch (e) {
      console.error(e);
    }
  };

  const executeOrchestrated = async (id: string) => {
    setExecuting(id);
    setExecResult(null);
    try {
      const r = await fetch(`${API_URL}/api/v1/planning/${id}/execute-orchestrated`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_parallel: 3, ensure_team: true }),
      });
      const data = await r.json();
      if (r.ok) {
        setExecResult(data.execution);
        setSelectedPlan(data.plan);
        fetchPlans();
      } else {
        setExecResult({ error: data.detail || "execution failed" });
      }
    } catch (e: any) {
      setExecResult({ error: e?.message || "network error" });
    } finally {
      setExecuting(null);
    }
  };

  if (loading) {
    return (
      <div className="p-4">
        <div className="text-center text-text-2">{t("loading") || "Loading..."}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header + filters (flexible: OS / Project layers) */}
      <div className="flex items-center justify-between p-4 border-b border-white/5 gap-2 flex-wrap">
        <h3 className="font-medium text-sm text-white">{t("planning.title") || "Planning"}</h3>
        <div className="flex gap-2 items-center flex-wrap">
          <select
            value={layerFilter}
            onChange={(e) => setLayerFilter(e.target.value)}
            className="text-xs rounded-lg px-2 py-1.5 border"
            style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)", color: "var(--text-1)" }}
          >
            <option value="all">all layers</option>
            <option value="os">os</option>
            <option value="project">project</option>
          </select>
          <input
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") fetchPlans(); }}
            placeholder="project_id filter"
            className="text-xs rounded-lg px-2 py-1.5 border w-32"
            style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)", color: "var(--text-0)" }}
          />
          <button
            onClick={() => setShowCreate(true)}
            className="px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors hover:border-[var(--accent)]"
            style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)", color: "var(--text-1)" }}
          >
            {t("planning.create_plan") || "Create Plan"}
          </button>
        </div>
      </div>

      {/* Plans List */}
      <div className="flex-1 overflow-y-auto p-4">
        {plans.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-text-2 mb-2">{t("planning.empty") || "No plans yet"}</p>
            <button
              onClick={() => setShowCreate(true)}
              className="text-xs text-accent hover:underline"
            >
              {t("planning.create_first") || "Create your first plan"}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="p-3 rounded-xl border"
                style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-sm text-white">{plan.name}</h4>
                    <p className="text-[10px] text-text-2 line-clamp-2">{plan.description}</p>
                  </div>
                  <div className="text-right">
                    <Badge
                      variant={plan.status === "active" ? "default" : "outline"}
                      className="text-[10px]"
                      style={{ background: plan.status === "active" ? "var(--accent)" : "transparent", borderColor: "var(--accent)" }}
                    >
                      {plan.status}
                    </Badge>
                  </div>
                </div>
                
                {/* Progress */}
                <div className="mt-2">
                  <div className="text-[10px] text-text-2 mb-1">
                    {plan.progress.completed}/{plan.progress.total} {t("planning.completed") || "tasks"}
                  </div>
                  <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${plan.progress.percent}%`,
                        background: plan.progress.percent === 100 ? "#10b981" : "var(--accent)",
                      }}
                    />
                  </div>
                </div>
                <div className="flex gap-2 mt-2 flex-wrap">
                  <button
                    onClick={() => viewPlan(plan.id)}
                    className="px-2 py-1 rounded-lg border text-[11px]"
                    style={{ borderColor: "var(--border-glass)", color: "var(--text-1)" }}
                  >
                    {t("planning.view_details") || "Details"}
                  </button>
                  <button
                    onClick={() => executeOrchestrated(plan.id)}
                    disabled={executing === plan.id}
                    className="px-2 py-1 rounded-lg text-[11px] font-medium bg-emerald-600 text-white disabled:opacity-50"
                  >
                    {executing === plan.id ? "Running..." : (t("planning.execute") || "Execute (team)")}
                  </button>
                  <button
                    onClick={() => deletePlan(plan.id)}
                    className="px-2 py-1 rounded-lg text-[11px] text-red-400 border border-red-500/20"
                  >
                    {t("planning.delete") || "Delete"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {execResult && (
          <div className="mt-3 p-3 rounded-xl border text-xs" style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)", color: "var(--text-1)" }}>
            <div className="font-medium mb-1">Execution result</div>
            <pre className="whitespace-pre-wrap break-words text-[11px]">{JSON.stringify(execResult, null, 2).slice(0, 2000)}</pre>
            <button onClick={() => setExecResult(null)} className="mt-2 text-[11px] underline">dismiss</button>
          </div>
        )}
        {selectedPlan && (
          <div className="mt-3 p-3 rounded-xl border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
            <div className="flex items-center justify-between mb-2">
              <div className="font-medium text-sm text-white">{selectedPlan.name}</div>
              <button onClick={() => setSelectedPlan(null)} className="text-[11px] text-text-2">close</button>
            </div>
            <div className="space-y-1">
              {selectedPlan.tasks?.map((task: Task) => (
                <div key={task.id} className="text-[11px] flex items-center justify-between gap-2 p-1.5 rounded bg-white/[0.03]">
                  <span style={{ color: "var(--text-0)" }}>{task.name} <span className="text-text-2">({task.agent_role})</span></span>
                  <span className="text-text-2">{task.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create Plan Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div 
            className="rounded-xl p-6 w-full max-w-md mx-4"
            style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)", borderWidth: "1px" }}
          >
            <h3 className="font-medium text-sm mb-4 text-white">{t("planning.create_mode") || "Create Mode"}</h3>
            
            <div className="space-y-3 mb-4">
              <input
                type="text"
                placeholder={t("planning.plan_name") || "Plan name..."}
                value={newPlanName}
                onChange={(e) => setNewPlanName(e.target.value)}
                className="w-full rounded-lg px-3 py-2 text-sm"
                style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)", color: "var(--text-0)" }}
              />
              <textarea
                placeholder={t("planning.plan_goal") || "Describe your goal..."}
                value={newPlanGoal}
                onChange={(e) => setNewPlanGoal(e.target.value)}
                rows={3}
                className="w-full rounded-lg px-3 py-2 text-sm resize-none"
                style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)", color: "var(--text-0)" }}
              />
            </div>
            
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium border"
                style={{ borderColor: "var(--border-glass)", color: "var(--text-2)" }}
              >
                {t("cancel") || "Cancel"}
              </button>
              <button
                onClick={decomposeGoal}
                disabled={!newPlanGoal}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-accent text-black"
              >
                {t("planning.decompose") || "AI Decompose"}
              </button>
              <button
                onClick={createPlan}
                disabled={!newPlanName || !newPlanGoal}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-primary text-white"
              >
                {t("planning.create") || "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { Badge } from "@/components/ui/badge";