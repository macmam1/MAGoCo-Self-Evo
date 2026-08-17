import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Settings, Play, Pause, Trash2, RefreshCw, Search, Filter, Package, Zap, Brain, Cog, Link, BarChart, Puzzle, Plus } from "lucide-react";

interface Skill {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  scope: string;
  tags: string[];
  enabled: boolean;
  entry_points: Array<{name: string; description: string}>;
  source: string;
  author: string;
}

const CATEGORY_ICONS: Record<string, any> = {
  "agent": Brain,
  "tool": Zap,
  "workflow": Settings,
  "integration": Link,
  "memory": Package,
  "evolution": Cog,
  "utility": BarChart,
  "custom": Puzzle,
};

const CATEGORY_LABELS: Record<string, string> = {
  agent: "Agent",
  tool: "Tool",
  workflow: "Workflow",
  integration: "Integration",
  memory: "Memory",
  evolution: "Evolution",
  utility: "Utility",
  custom: "Custom",
};

export function SkillsDashboard() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [showEnabled, setShowEnabled] = useState(true);

  useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (showEnabled) params.set("enabled_only", "true");
      const resp = await fetch(`/api/v1/skills/?${params.toString()}`);
      const data = await resp.json();
      setSkills(data);
    } catch (err) {
      console.error("Failed to load skills:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSkill = async (skillId: string, enable: boolean) => {
    try {
      const action = enable ? "enable" : "disable";
      await fetch(`/api/v1/skills/${skillId}/${action}`, { method: "POST" });
      setSkills(skills.map(s =>
        s.id === skillId ? { ...s, enabled: enable } : s
      ));
    } catch (err) {
      console.error("Failed to toggle skill:", err);
    }
  };

  const handleReload = async () => {
    try {
      await fetch(`/api/v1/skills/reload`, { method: "POST" });
      fetchSkills();
    } catch (err) {
      console.error("Failed to reload skills:", err);
    }
  };

  const filtered = skills.filter(s => {
    const matchesSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.tags.some(t => t.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesCategory = activeCategory === "all" || s.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  const categories = [
    { id: "all", label: "All Skills", count: skills.length },
    ...Object.entries(CATEGORY_LABELS).map(([id, label]) => ({
      id,
      label,
      count: skills.filter(s => s.category === id).length,
    })),
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="h-6 w-6 animate-spin text-indigo-400" />
      </div>
    );
  }

  return (
    <div className="p-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Skills Marketplace</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage and configure your MAGoCo skills
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReload}
            className="px-3 py-2 bg-[#15151f] border border-[#1f1f2e] rounded-lg hover:bg-[#1a1a2e] transition flex items-center gap-2 text-sm"
          >
            <RefreshCw className="h-3 w-3" />
            Reload
          </button>
          <button className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg transition flex items-center gap-2 text-sm">
            <Plus className="h-3 w-3" />
            Install
          </button>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search skills..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#15151f] border border-[#1f1f2e] rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={showEnabled}
            onChange={(e) => setShowEnabled(e.target.checked)}
            className="rounded bg-[#15151f] border-[#1f1f2e] text-indigo-600"
          />
          Enabled only
        </label>
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {categories.map(cat => {
          const Icon = CATEGORY_ICONS[cat.id] || Package;
          return (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-3 py-2 rounded-lg flex items-center gap-2 text-sm whitespace-nowrap transition-all ${
                activeCategory === cat.id
                  ? "bg-indigo-600/10 text-indigo-400 border border-indigo-500/20"
                  : "text-slate-400 hover:bg-[#15151f] hover:text-slate-200 border border-transparent"
              }`}
            >
              <Icon className="h-4 w-4" />
              {cat.label} ({cat.count})
            </button>
          );
        })}
      </div>

      {/* Skills Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(skill => {
          const Icon = CATEGORY_ICONS[skill.category] || Package;
          return (
            <div
              key={skill.id}
              className={`p-4 bg-[#15151f] border rounded-xl transition-all ${
                skill.enabled
                  ? "border-[#1f1f2e] hover:border-[#2a2a3e]"
                  : "border-[#1f1f2e] opacity-60"
              }}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-indigo-600/10 rounded-lg">
                    <Icon className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-slate-200">{skill.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant={skill.enabled ? "default" : "secondary"}>
                        {skill.enabled ? "Enabled" : "Disabled"}
                      </Badge>
                      <span className="text-xs text-slate-600">v{skill.version}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => toggleSkill(skill.id, !skill.enabled)}
                  className={`p-1 rounded transition ${
                    skill.enabled
                      ? "text-green-400 hover:bg-green-900/20"
                      : "text-slate-500 hover:bg-[#1a1a2e]"
                  }`}
                  title={skill.enabled ? "Disable" : "Enable"}
                >
                  {skill.enabled ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                </button>
              </div>

              <p className="text-sm text-slate-400 mb-3 line-clamp-2">
                {skill.description}
              </p>

              {skill.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {skill.tags.slice(0, 3).map(tag => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {skill.tags.length > 3 && (
                    <Badge variant="outline" className="text-xs">
                      +{skill.tags.length - 3}
                    </Badge>
                  )}
                </div>
              )}

              {skill.entry_points.length > 0 && (
                <div className="text-xs text-slate-500">
                  Entry points: {skill.entry_points.map(ep => ep.name).join(", ")}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          <Package className="h-8 w-8 mx-auto mb-3 opacity-30" />
          <p>No skills found matching your search</p>
        </div>
      )}
    </div>
  );
}