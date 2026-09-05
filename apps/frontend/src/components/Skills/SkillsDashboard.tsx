import { useState, useEffect } from "react";
import { 
  Search, Filter, Plus, Star, Download, Upload, 
  Tag, Package, Code, Globe, Zap, Shield,
  ChevronRight, ExternalLink, Eye, Edit, Trash2,
  Menu, X, Filter as FilterIcon
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button, Badge, Card, CardHeader, CardTitle, CardContent, Input } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { SkillsTabs } from "./SkillsTabs";
import { SkillCard } from "./SkillCard";
import { SkillBuilder } from "./SkillBuilder";
import { SkillMarketplace } from "./SkillMarketplace";

export function SkillsDashboard() {
  const { t } = useTranslation();
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    query: "",
    category: "",
    type: "",
    free_only: false,
    featured_only: false,
    sort_by: "relevance",
    sort_order: "desc",
  });
  const [pagination, setPagination] = useState({ page: 1, total: 0, page_size: 20 });
  const [activeView, setActiveView] = useState<"grid" | "list">("grid");
  const [showBuilder, setShowBuilder] = useState(false);
  const [showMarketplace, setShowMarketplace] = false;
  const [selectedSkill, setSelectedSkill] = useState<any>(null);
  const [showSkillDetail, setShowSkillDetail] = useState(false);

  const fetchSkills = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: pagination.page.toString(),
        page_size: pagination.page_size.toString(),
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      });
      
      if (filters.query) params.append("query", filters.query);
      if (filters.category) params.append("category", filters.category);
      if (filters.type) params.append("type", filters.type);
      if (filters.free_only) params.append("free_only", "true");
      if (filters.featured_only) params.append("featured_only", "true");
      
      const response = await fetch(`/api/v1/skills?${params}`);
      if (response.ok) {
        const data = await response.json();
        setSkills(data);
        setPagination(prev => ({ ...prev, total: data.length * 10 })); // estimate
      }
    } catch (error) {
      console.error("Failed to fetch skills:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSkills();
  }, [pagination.page, filters.query, filters.category, filters.type]);

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleSkillClick = (skill: any) => {
    setSelectedSkill(skill);
    setShowSkillDetail(true);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center">
            <Package className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="font-medium text-sm text-white">{t("skills.system")}</h2>
            <p className="text-xs text-text-2">{t("skills.subtitle")}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={() => setShowMarketplace(true)}>
            <Globe className="h-4 w-4 mr-1" /> {t("skills.marketplace")}
          </Button>
          <Button variant="primary" size="sm" onClick={() => setShowBuilder(true)}>
            <Plus className="h-4 w-4 mr-1" /> {t("skills.create_skill")}
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 p-4 border-b border-white/5 flex-wrap">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-2" />
          <input
            type="text"
            value={filters.query}
            onChange={(e) => handleFilterChange("query", e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchSkills()}
            placeholder={t("skills.search_placeholder")}
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-10 py-2 focus:ring-2 focus:ring-primary"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <select
            value={filters.category}
            onChange={(e) => handleFilterChange("category", e.target.value)}
            className="bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary text-sm"
          >
            <option value="">{t("skills.all_categories")}</option>
            {Object.values(t("skills.categories") || {}).map((cat: string) => (
              <option key={cat} value={cat.toLowerCase().replace(" ", "_")}>{cat}</option>
            ))}
          </select>

          <select
            value={filters.type}
            onChange={(e) => handleFilterChange("type", e.target.value)}
            className="bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary text-sm"
          >
            <option value="">{t("skills.all_types")}</option>
            {Object.values(t("skills.types") || {}).map((type: string) => (
              <option key={type} value={type.toLowerCase().replace(" ", "_")}>{type}</option>
            ))}
          </select>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 text-sm text-text-2">
              <input
                type="checkbox"
                checked={filters.free_only}
                onChange={(e) => handleFilterChange("free_only", e.target.checked)}
                className="rounded border-white/20"
              />
              {t("skills.free_only")}
            </label>
            <label className="flex items-center gap-1 text-sm text-text-2">
              <input
                type="checkbox"
                checked={filters.featured_only}
                onChange={(e) => handleFilterChange("featured_only", e.target.checked)}
                className="rounded border-white/20"
              />
              {t("skills.featured_only")}
            </label>
          </div>

          <div className="flex items-center gap-1">
            <label className="text-xs text-text-2">{t("skills.sort_by")}</label>
            <select
              value={filters.sort_by}
              onChange={(e) => handleFilterChange("sort_by", e.target.value)}
              className="bg-gray-800/50 border border-white/10 rounded-lg px-2 py-1 text-xs focus:ring-2 focus:ring-primary"
            >
              <option value="relevance">{t("skills.relevance")}</option>
              <option value="rating">{t("skills.rating")}</option>
              <option value="downloads">{t("skills.downloads")}</option>
              <option value="updated">{t("skills.recently_updated")}</option>
              <option value="created">{t("skills.newest")}</option>
            </select>
            <select
              value={filters.sort_order}
              onChange={(e) => handleFilterChange("sort_order", e.target.value)}
              className="bg-gray-800/50 border border-white/10 rounded-lg px-2 py-1 text-xs focus:ring-2 focus:ring-primary"
            >
              <option value="desc">{t("skills.descending")}</option>
              <option value="asc">{t("skills.ascending")}</option>
            </select>
          </div>

          <Button variant="outline" size="sm" onClick={fetchSkills} disabled={loading}>
            <FilterIcon className="h-4 w-4 mr-1" /> {t("skills.apply_filters")}
          </Button>
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
        <div className="flex items-center gap-1">
          <Button
            variant={activeView === "grid" ? "primary" : "outline"}
            size="sm"
            onClick={() => setActiveView("grid")}
          >
            <Package className="h-4 w-4" />
          </Button>
          <Button
            variant={activeView === "list" ? "primary" : "outline"}
            size="sm"
            onClick={() => setActiveView("list")}
          >
            <Tag className="h-4 w-4" />
          </Button>
        </div>
        <div className="text-xs text-text-2">
          {t("skills.showing")} {skills.length} {t("skills.of")} {pagination.total}
        </div>
      </div>

      {/* Skills Grid/List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin h-8 w-8 border-b-2 border-current" />
          </div>
        )}

        {!loading && skills.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 text-text-2">
            <Package className="w-12 h-12 mb-3 opacity-30" />
            <p>{t("skills.no_skills_found")}</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={() => setShowBuilder(true)}>
              <Plus className="h-4 w-4 mr-1" /> {t("skills.create_first_skill")}
            </Button>
          </div>
        )}

        {activeView === "grid" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {skills.map((skillData: any) => (
              <SkillCard
                key={skillData.skill.id || skillData.id}
                skill={skillData.skill || skillData}
                onClick={() => handleSkillClick(skillData.skill || skillData)}
              />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {skills.map((skillData: any) => (
              <SkillListItem
                key={skillData.skill.id || skillData.id}
                skill={skillData.skill || skillData}
                onClick={() => handleSkillClick(skillData.skill || skillData)}
              />
            ))}
          </div>
        )}

        {!loading && skills.length > 0 && (
          <div className="flex items-center justify-center mt-4 gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))}
              disabled={pagination.page <= 1}
            >
              <ChevronRight className="h-4 w-4" style={{ transform: "rotate(180deg)" }} /> {t("skills.previous")}
            </Button>
            <span className="px-3 text-sm text-text-2">
              {t("skills.page")} {pagination.page}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPagination(p => ({ ...p, page: p.page + 1 }))}
              disabled={skills.length < pagination.page_size}
            >
              {t("skills.next")} <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>

      {/* Skill Detail Modal */}
      <SkillDetailModal
        skill={selectedSkill}
        isOpen={showSkillDetail}
        onClose={() => { setShowSkillDetail(false); setSelectedSkill(null); }}
      />

      {/* Skill Builder Modal */}
      <SkillBuilder
        isOpen={showBuilder}
        onClose={() => setShowBuilder(false)}
        onSuccess={() => { setShowBuilder(false); fetchSkills(); }}
      />

      {/* Marketplace Modal */}
      <SkillMarketplace
        isOpen={showMarketplace}
        onClose={() => setShowMarketplace(false)}
        onInstall={(skillId) => { fetchSkills(); }}
      />
    </div>
  );
}

function SkillListItem({ skill, onClick }: { skill: any; onClick: () => void }) {
  const { t } = useTranslation();
  
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 p-3 rounded-lg border hover:border-[var(--accent)] transition-colors cursor-pointer"
      style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
    >
      <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
           style={{ background: "linear-gradient(135deg, #7c5cff, #a855f7)" }}>
        <Package className="h-5 w-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate" style={{ color: "var(--text-0)" }}>
            {skill.display_name || skill.name}
          </span>
          <Badge variant="outline" className="text-[10px] capitalize">{skill.category}</Badge>
          <Badge variant="secondary" className="text-[10px]">{skill.type}</Badge>
          {skill.featured && <Badge variant="secondary" className="text-[10px]"><Star className="h-3 w-3 mr-1" /> {t("skills.featured")}</Badge>}
          {skill.price === 0 && <Badge variant="outline" className="text-[10px]">{t("skills.free")}</Badge>}
        </div>
        <p className="text-xs text-text-2 truncate mt-1">{skill.description}</p>
        <div className="flex items-center gap-3 mt-1 text-[10px] text-text-2">
          <span>⭐ {skill.rating?.toFixed(1) || "0.0"}</span>
          <span>⬇ {skill.downloads || 0}</span>
          <span className="capitalize">{skill.status}</span>
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-text-2" />
    </button>
  );
}

function SkillDetailModal({ skill, isOpen, onClose }: { skill: any; isOpen: boolean; onClose: () => void }) {
  const { t } = useTranslation();

  if (!isOpen || !skill) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={skill.display_name || skill.name} size="xl">
      <div className="p-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-3 flex-wrap">
              <Badge variant="outline" className="capitalize">{skill.category}</Badge>
              <Badge variant="secondary" className="capitalize">{skill.type}</Badge>
              {skill.featured && <Badge variant="primary"><Star className="h-3 w-3 mr-1" /> Featured</Badge>}
              {skill.price > 0 ? (
                <Badge variant="secondary">{skill.price} {skill.currency}</Badge>
              ) : (
                <Badge variant="outline" style={{ background: "#22c55e20", borderColor: "#22c55e", color: "#22c55e" }}>
                  Free
                </Badge>
              )}
              <Badge variant="outline" className="capitalize">{skill.status}</Badge>
            </div>

            <p className="text-text-0 whitespace-pre-wrap">{skill.description}</p>

            <div className="flex flex-wrap gap-2">
              {(skill.tags || []).slice(0, 10).map((tag: string) => (
                <Badge key={tag} variant="outline" className="text-[10px]">#{tag}</Badge>
              ))}
            </div>

            <div className="border-t border-white/5 pt-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-text-2">{t("skills.author")}</span>
                <span className="font-medium">{skill.author}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-2">{t("skills.version")}</span>
                <span className="font-medium">{skill.version}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-2">{t("skills.downloads")}</span>
                <span className="font-medium">{skill.downloads || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-2">{t("skills.rating")}</span>
                <span className="font-medium">⭐ {skill.rating?.toFixed(1) || "0.0"} ({skill.review_count || 0} {t("skills.reviews")})</span>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl border"
                 style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
              <h4 className="font-medium mb-3">{t("skills.quick_actions")}</h4>
              <div className="flex flex-wrap gap-2">
                <button className="px-4 py-2 bg-gradient-to-r from-accent to-accent-2 text-black font-medium rounded-lg hover:shadow-lg">
                  {t("skills.install")}
                </button>
                <button className="px-4 py-2 border border-white/10 text-text-0 font-medium rounded-lg hover:bg-white/5">
                  {t("skills.view_code")}
                </button>
                <button className="px-4 py-2 border border-white/10 text-text-0 font-medium rounded-lg hover:bg-white/5">
                  {t("skills.read_reviews")}
                </button>
              </div>
            </div>

            {skill.requirements && skill.requirements.length > 0 && (
              <div className="p-4 rounded-xl border"
                   style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                <h4 className="font-medium mb-2">{t("skills.requirements")}</h4>
                <div className="flex flex-wrap gap-1">
                  {skill.requirements.map((req: string) => (
                    <Badge key={req} variant="outline" className="text-[10px]">{req}</Badge>
                  ))}
                </div>
              </div>
            )}

            {skill.parameters && skill.parameters.length > 0 && (
              <div className="p-4 rounded-xl border"
                   style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                <h4 className="font-medium mb-2">{t("skills.parameters")}</h4>
                <div className="space-y-2">
                  {skill.parameters.map((param: any) => (
                    <div key={param.name} className="flex items-center justify-between text-sm">
                      <span className="font-medium">{param.name}</span>
                      <span className="text-text-2">{param.type} {param.required ? "· required" : "· optional"}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {skill.examples && skill.examples.length > 0 && (
              <div className="p-4 rounded-xl border"
                   style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                <h4 className="font-medium mb-2">{t("skills.examples")}</h4>
                <div className="space-y-2">
                  {skill.examples.map((ex: any, i: number) => (
                    <div key={i} className="p-3 rounded-lg"
                         style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}>
                      <div className="font-medium mb-1">{ex.name}</div>
                      <p className="text-sm text-text-2">{ex.description}</p>
                      <pre className="mt-2 p-2 rounded text-[10px] overflow-x-auto"
                           style={{ background: "var(--bg-0)" }}>
                        {JSON.stringify(ex.input_data, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}