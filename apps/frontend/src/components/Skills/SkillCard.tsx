import { Star, Download, ExternalLink, Tag, Zap, Shield, Globe, Code } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface SkillCardProps {
  skill: any;
  onClick: () => void;
}

export function SkillCard({ skill, onClick }: SkillCardProps) {
  const { t } = useTranslation();
  
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

  const getCategoryIcon = (category: string) => {
    const icons: Record<string, any> = {
      automation: Zap,
      coding: Code,
      data_processing: Globe,
      web_scraping: Globe,
      api_integration: Globe,
      file_operations: Globe,
      system_admin: Shield,
      ai_ml: Zap,
      communication: Zap,
      productivity: Zap,
      development: Code,
      security: Shield,
      monitoring: Zap,
      custom: Tag,
    };
    return icons[category] || Package;
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        "relative p-4 rounded-xl border transition-all duration-200 hover:border-[var(--accent)]",
        "flex flex-col h-full cursor-pointer overflow-hidden"
      )}
      style={{ 
        background: "var(--bg-1)", 
        borderColor: "var(--border-glass)",
        borderLeft: `3px solid ${getTypeColor(skill.type || "function")}`,
      }}
    >
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
      </div>

      {/* Description */}
      <p className="text-sm text-text-2 line-clamp-2 mb-3 flex-1">
        {skill.description}
      </p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1 mb-3">
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

      {/* Meta */}
      <div className="flex items-center justify-between pt-3 border-t border-white/5">
        <div className="flex items-center gap-3 text-[10px] text-text-2">
          <span className="flex items-center gap-1">
            <Download className="h-3 w-3" />
            {skill.downloads || 0}
          </span>
          <span className="flex items-center gap-1">
            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
            {skill.rating?.toFixed(1) || "0.0"}
          </span>
        </div>
        <div className="flex items-center gap-1">
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

      {/* Footer Actions */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
        <div className="flex items-center gap-1">
          {skill.price > 0 ? (
            <span className="text-sm font-medium text-green-400">${skill.price}</span>
          ) : (
            <Badge variant="secondary" className="text-[10px] px-2 py-0.5" 
                   style={{ background: "#22c55e20", borderColor: "#22c55e", color: "#22c55e" }}>
              Free
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Badge variant="outline" className="text-[9px]">{skill.version}</Badge>
        </div>
      </div>
    </button>
  );
}