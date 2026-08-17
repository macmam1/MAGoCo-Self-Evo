import { LayoutDashboard, MessageSquare, Code, Settings, Workflow, Bot, Link, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarItemProps {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  onClick?: () => void;
}

function SidebarItem({ icon: Icon, label, active, onClick }: SidebarItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
        active
          ? "bg-indigo-600/10 text-indigo-400 border border-indigo-500/20"
          : "text-slate-400 hover:bg-[#15151f] hover:text-slate-200"
      )}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </button>
  );
}

export function Sidebar({ currentTab, onTabChange }: { currentTab: string; onTabChange: (tab: string) => void }) {
  return (
    <div className="w-64 border-r border-[#1f1f2e] bg-[#0a0a0f] flex flex-col justify-between p-3 select-none">
      <div className="space-y-4">
        {/* Brand */}
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-slate-100 leading-none">MAGoCo</h1>
            <span className="text-[10px] text-indigo-400 font-medium">Self-Evo Studio</span>
          </div>
        </div>

        {/* Navigation */}
        <div className="space-y-1">
          <SidebarItem
            icon={MessageSquare}
            label="Agent Chat"
            active={currentTab === "chat"}
            onClick={() => onTabChange("chat")}
          />
          <SidebarItem
            icon={Code}
            label="Coding IDE"
            active={currentTab === "ide"}
            onClick={() => onTabChange("ide")}
          />
          <SidebarItem
            icon={Workflow}
            label="Workflows"
            active={currentTab === "workflows"}
            onClick={() => onTabChange("workflows")}
          />
          <SidebarItem
            icon={Settings}
            label="Settings & LLM"
            active={currentTab === "settings"}
            onClick={() => onTabChange("settings")}
          />
          <SidebarItem
            icon={MessageSquare}
            label="Approvals"
            active={currentTab === "approvals"}
            onClick={() => onTabChange("approvals")}
          />
          <SidebarItem
            icon={Link}
            label="Integrations"
            active={currentTab === "integrations"}
            onClick={() => onTabChange("integrations")}
          />
          <SidebarItem
            icon={Clock}
            label="Execution History"
            active={currentTab === "history"}
            onClick={() => onTabChange("history")}
          />
        </div>
      </div>
    </div>
  );
}
