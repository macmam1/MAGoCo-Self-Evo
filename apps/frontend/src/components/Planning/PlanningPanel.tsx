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

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/planning`);
      if (r.ok) setPlans(await r.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const createPlan = async () => {
    if (!newPlanName || !newPlanGoal) return;
    try {
      const r = await fetch(`${API_URL}/api/v1/planning/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newPlanName,
          description: newPlanGoal,
          layer: "os",
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
        }),
      });
      if (r.ok) {
        const plan = await r.json();
        fetchPlans();
        setSelectedPlan(plan);
        setShowCreate(false);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deletePlan = async (id: string) => {
    try {
      await fetch(`${API_URL}/api/v1/planning/${id}`, { method: "DELETE" });
      fetchPlans();
    } catch (e) {
      console.error(e);
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
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <h3 className="font-medium text-sm text-white">{t("planning.title") || "Planning"}</h3>
        <div className="flex gap-2">
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
              </div>
            ))}
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