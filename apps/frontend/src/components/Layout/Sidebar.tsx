import { useEffect, useState } from "react";
import { Bot, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { getDensity } from "@/theme/theme";

export interface SidebarTab {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
}

/** Group titles in first-seen order (tabs arrive pre-grouped). */
function groupOrder(tabs: SidebarTab[]): string[] {
  return [...new Set(tabs.map((t) => t.group))];
}

function SidebarItem({
  icon: Icon,
  label,
  badge,
  active,
  compact,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  badge?: string;
  active?: boolean;
  compact?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={compact ? label : undefined}
      className={cn(
        "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 border border-transparent",
        compact && "justify-center px-0",
        active
          ? "text-[var(--text-0)]"
          : "text-[var(--text-1)] hover:text-[var(--text-0)] hover:bg-white/[0.04]"
      )}
      style={active ? { background: "var(--bg-2)", borderColor: "var(--border-glass)" } : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" style={active ? { color: "var(--accent)" } : undefined} />
      {!compact && <span className="flex-1 text-left">{label}</span>}
      {!compact && badge && (
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
          style={{ background: "color-mix(in srgb, var(--accent) 15%, transparent)", color: "var(--accent)" }}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

export function Sidebar({
  tabs,
  activeTab,
  onTabChange,
  browserSessions = 0,
}: {
  tabs: SidebarTab[];
  activeTab: string;
  onTabChange: (tab: string) => void;
  browserSessions?: number;
}) {
  const [compact, setCompact] = useState(getDensity() === "compact");
  const [storedBrowserSessions, setStoredBrowserSessions] = useLocalStorage(
    "browser-sessions-count",
    browserSessions
  );

  useEffect(() => {
    setStoredBrowserSessions(browserSessions);
  }, [browserSessions]);

  useEffect(() => {
    const onChange = (e: Event) =>
      setCompact((e as CustomEvent<string>).detail === "compact");
    window.addEventListener("magoco:density", onChange);
    return () => window.removeEventListener("magoco:density", onChange);
  }, []);

  return (
    <div
      className={cn(
        "border-r flex flex-col justify-between p-3 select-none shrink-0 transition-all",
        compact ? "w-16" : "w-60"
      )}
      style={{ borderColor: "var(--border-glass)", background: "var(--bg-1)" }}
    >
      <div className="space-y-5 overflow-y-auto">
        {/* Brand */}
        <div className={cn("flex items-center gap-2.5 px-2 pt-1", compact && "justify-center px-0")}>
          <div
            className="h-8 w-8 rounded-[10px] flex items-center justify-center shadow-lg shrink-0"
            style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-2))" }}
          >
            <Bot className="h-4 w-4 text-white" />
          </div>
          {!compact && (
            <div>
              <h1 className="font-bold text-sm leading-none" style={{ color: "var(--text-0)" }}>
                MAGoCo
              </h1>
              <span className="text-[10px] font-medium" style={{ color: "var(--accent)" }}>
                Self-Evo Studio
              </span>
            </div>
          )}
        </div>

        {/* Model pill (LucidAI pattern) */}
        {!compact && (
          <button
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium border"
            style={{
              background: "var(--bg-2)",
              borderColor: "var(--border-glass)",
              color: "var(--text-1)",
            }}
          >
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              9Router · Auto
            </span>
            <Badge variant="default" className="h-2.5 w-2.5 rounded-full">
              {storedBrowserSessions > 0 && <span>{storedBrowserSessions}</span>}
            </Badge>
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
        )}

        {/* Grouped nav (NeuroNest pattern) */}
        {groupOrder(tabs).map((title) => {
          const items = tabs.filter((t) => t.group === title);
          if (items.length === 0) return null;
          return (
            <div key={title} className="space-y-1">
              <div
                className="px-3 text-[10px] font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-2)" }}
              >
                {title}
              </div>
              {items.map((t) => (
                <SidebarItem
                  key={t.id}
                  icon={t.icon}
                  label={t.label}
                  badge={t.id === "approvals" ? "3" : undefined}
                  active={activeTab === t.id}
                  compact={compact}
                  onClick={() => onTabChange(t.id)}
                />
              ))}
            </div>
          );
        })}
      </div>

      {/* User card (Ask Rune pattern) */}
      <div
        className={cn("flex items-center gap-2.5 p-2.5 rounded-xl border mt-3", compact && "justify-center")}
        style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}
      >
        <div
          className="h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
          style={{ background: "linear-gradient(135deg, var(--accent-2), var(--accent-3))" }}
        >
          U
        </div>
        {!compact && (
          <div className="min-w-0">
            <div className="text-xs font-semibold truncate" style={{ color: "var(--text-0)" }}>
              Operator
            </div>
            <div className="text-[10px] truncate" style={{ color: "var(--text-2)" }}>
              local workspace
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
