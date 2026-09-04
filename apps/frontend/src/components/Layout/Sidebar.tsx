import { Bot, ChevronDown, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SidebarTab {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
}

const GROUPS = ["General", "Operations", "System"];

function SidebarItem({
  icon: Icon,
  label,
  badge,
  active,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  badge?: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 border border-transparent",
        active
          ? "text-[var(--text-0)]"
          : "text-[var(--text-1)] hover:text-[var(--text-0)] hover:bg-white/[0.04]"
      )}
      style={active ? { background: "var(--bg-2)", borderColor: "var(--border-glass)" } : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" style={active ? { color: "var(--accent)" } : undefined} />
      <span className="flex-1 text-left">{label}</span>
      {badge && (
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
}: {
  tabs: SidebarTab[];
  activeTab: string;
  onTabChange: (tab: string) => void;
}) {
  return (
    <div
      className="w-60 border-r flex flex-col justify-between p-3 select-none shrink-0"
      style={{ borderColor: "var(--border-glass)", background: "var(--bg-1)" }}
    >
      <div className="space-y-5 overflow-y-auto">
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-2 pt-1">
          <div
            className="h-8 w-8 rounded-[10px] flex items-center justify-center shadow-lg"
            style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-2))" }}
          >
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-sm leading-none" style={{ color: "var(--text-0)" }}>
              MAGoCo
            </h1>
            <span className="text-[10px] font-medium" style={{ color: "var(--accent)" }}>
              Self-Evo Studio
            </span>
          </div>
        </div>

        {/* Model pill (LucidAI pattern) */}
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
          <ChevronDown className="h-3.5 w-3.5" />
        </button>

        {/* Grouped nav (NeuroNest pattern) */}
        {GROUPS.map((title) => {
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
                  onClick={() => onTabChange(t.id)}
                />
              ))}
            </div>
          );
        })}
      </div>

      {/* User card (Ask Rune pattern) */}
      <div
        className="flex items-center gap-2.5 p-2.5 rounded-xl border mt-3"
        style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}
      >
        <div
          className="h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
          style={{ background: "linear-gradient(135deg, var(--accent-2), var(--accent-3))" }}
        >
          U
        </div>
        <div className="min-w-0">
          <div className="text-xs font-semibold truncate" style={{ color: "var(--text-0)" }}>
            Operator
          </div>
          <div className="text-[10px] truncate" style={{ color: "var(--text-2)" }}>
            local workspace
          </div>
        </div>
      </div>
    </div>
  );
}
