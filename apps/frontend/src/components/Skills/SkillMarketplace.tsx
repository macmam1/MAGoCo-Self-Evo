import { useState, useEffect } from "react";
import { X, Search, Download, Star, Package, Shield, Zap, Globe, Code, ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button, Badge, Card, CardHeader, CardTitle, CardContent, Input } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";

interface SkillMarketplaceProps {
  isOpen: boolean;
  onClose: () => void;
  onInstall: (skillId: string) => void;
}

export function SkillMarketplace({ isOpen, onClose, onInstall }: SkillMarketplaceProps) {
  const { t } = useTranslation();
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    query: "",
    category: "",
    free_only: false,
    featured_only: false,
    sort_by: "relevance",
    sort_order: "desc",
  });
  const [pagination, setPagination] = useState({ page: 1, total: 0, page_size: 12 });

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
      if (filters.free_only) params.append("free_only", "true");
      if (filters.featured_only) params.append("featured_only", "true");
      
      const response = await fetch(`/api/v1/skills?${params}`);
      if (response.ok) {
        const data = await response.json();
        setSkills(data);
        setPagination(prev => ({ ...prev, total: data.length * 10 }));
      }
    } catch (error) {
      console.error("Failed to fetch marketplace skills:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSkills();
  }, [pagination.page, filters.query, filters.category]);

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleInstall = async (skillId: string) => {
    try {
      // In a real app, this would call the install endpoint
      // For now, just call the onInstall callback
      onInstall(skillId);
    } catch (error) {
      console.error("Install failed:", error);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t("skills.marketplace")}
      size="full"
    >
      <div className="h-full flex flex-col">
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
              <option value="automation">Automation</option>
              <option value="coding">Coding</option>
              <option value="data_processing">Data Processing</option>
              <option value="web_scraping">Web Scraping</option>
              <option value="api_integration">API Integration</option>
              <option value="file_operations">File Operations</option>
              <option value="system_admin">System Admin</option>
              <option value="ai_ml">AI/ML</option>
              <option value="communication">Communication</option>
              <option value="productivity">Productivity</option>
              <option value="development">Development</option>
              <option value="security">Security</option>
              <option value="monitoring">Monitoring</option>
              <option value="custom">Custom</option>
            </select>

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

            <select
              value={filters.sort_by}
              onChange={(e) => handleFilterChange("sort_by", e.target.value)}
              className="bg-gray-800/50 border border-white/10 rounded-lg px-2 py-2 text-xs focus:ring-2 focus:ring-primary"
            >
              <option value="relevance">{t("skills.relevance")}</option>
              <option value="rating">{t("skills.rating")}</option>
              <option value="downloads">{t("skills.downloads")}</option>
              <option value="updated">{t("skills.recently_updated")}</option>
              <option value="created">{t("skills.newest")}</option>
            </select>
          </div>
        </div>

        {/* Skills Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin h-8 w-8 border-b-2 border-current" />
            </div>
          )}

          {!loading && skills.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 text-text-2">
              <Package className="w-12 h-12 mb-3 opacity-30" />
              <p>{t("skills.no_skills")}</p>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {skills.map((skillData: any) => (
              <MarketplaceSkillCard
                key={skillData.skill.id || skillData.id}
                skill={skillData.skill || skillData}
                onInstall={handleInstall}
              />
            ))}
          </div>

          {!loading && skills.length > 0 && (
            <div className="flex items-center justify-center mt-4 gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))}
                disabled={pagination.page <= 1}
              >
                {t("skills.previous")}
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
                {t("skills.next")}
              </Button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

function MarketplaceSkillCard({ skill, onInstall }: { skill: any; onInstall: (id: string) => void }) {
  const { t } = useTranslation();
  const [installing, setInstalling] = useState(false);

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      function: "#7c5cff",
      workflow: "#f5a524",
      agent: "#22d3ee",
      template: "#34d399",
      prompt: "#8b5cf6",
      tool: "#ec4899",
      chain: "#6366f1",
    };
    return colors[type] || "#7c5cff";
  };

  const handleInstall = async () => {
    setInstalling(true);
    try {
      await onInstall(skill.id || skill.skill?.id);
    } finally {
      setInstalling(false);
    }
  };

  return (
    <div className="relative p-4 rounded-xl border hover:border-[var(--accent)] transition-colors h-full flex flex-col"
         style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
               style={{ background: `linear-gradient(135deg, ${getTypeColor(skill.type || "function")}20, ${getTypeColor(skill.type || "function")}10)` }}>
            <Package className="h-4 w-4" style={{ color: getTypeColor(skill.type || "function") }} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm truncate" style={{ color: "var(--text-0)" }}>
              {skill.display_name || skill.name}
            </h3>
            <div className="flex items-center gap-1 mt-0.5">
              <Badge variant="outline" className="text-[9px] capitalize" 
                     style={{ borderColor: getTypeColor(skill.type || "function"), color: getTypeColor(skill.type || "function") }}>
                {skill.type}
              </Badge>
              <Badge variant="outline" className="text-[9px] capitalize" 
                     style={{ borderColor: "#f5a524", color: "#f5a524" }}>
                {skill.category}
              </Badge>
            </div>
          </div>
        </div>
        
        {skill.featured && (
          <div className="absolute top-3 right-3">
            <Star className="h-3 w-3 text-yellow-400" />
          </div>
        )}

      {/* Description */}
      <p className="text-sm text-text-2 line-clamp-2 mb-3">
        {skill.description}
      </p>

      {/* Stats */}
      <div className="flex items-center gap-3 mb-3 text-[10px] text-text-2">
        <span className="flex items-center gap-1">
          <Download className="h-3 w-3" />
          {skill.downloads || 0}
        </span>
        <span className="flex items-center gap-1">
          <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
          {skill.rating?.toFixed(1) || "0.0"}
        </span>
        <span className="flex items-center gap-1">
          <Shield className="h-3 w-3" />
          {skill.security_level || "restricted"}
        </span>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1 mb-4">
        {(skill.tags || []).slice(0, 4).map((tag: string) => (
          <Badge key={tag} variant="outline" className="text-[9px] px-1.5 py-0.5">
            #{tag}
          </Badge>
        ))}
        {(skill.tags || []).length > 4 && (
          <Badge variant="outline" className="text-[9px] text-text-2">
            +{(skill.tags || []).length - 4}
          </Badge>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-white/5 mt-auto">
        <div className="flex items-center gap-1">
          {skill.price > 0 ? (
            <span className="text-sm font-medium text-green-400">${skill.price}</span>
          ) : (
            <Badge variant="secondary" className="text-[10px] px-2 py-0.5" 
                   style={{ background: "#22c55e20", borderColor: "#22c55e", color: "#22c55e" }}>
              {t("skills.free")}
            </Badge>
          )}
        </div>
        <button
          onClick={handleInstall}
          disabled={installing}
          className="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors"
          style={{ 
            background: "linear-gradient(135deg, var(--accent), var(--accent-2))",
            color: "black",
          }}
        >
          {installing ? t("skills.installing") : t("skills.install")}
        </button>
      </div>
    </div>
  );
}