import { LayoutDashboard, MessageSquare, Code, Settings, LogOut, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface SidebarItemProps {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  collapsed?: boolean;
  onClick?: () => void;
}

function SidebarItem({ icon: Icon, label, active, collapsed, onClick }: SidebarItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 group text-sm font-medium",
        active
          ? "bg-primary-500/20 text-primary-400 border border-primary-500/10"
          : "text-text-2 hover:bg-white/5 hover:text-text-0"
      )}
    >
      <Icon
        size={18}
        className={cn(
          "transition-transform duration-200 group-hover:scale-110",
          active ? "text-primary-400" : "text-text-2 group-hover:text-text-0"
        )}
      />
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  );
}

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

export function Sidebar({ currentTab, onTabChange }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className={cn(
        "h-screen glass-soft border-r border-white/5 flex flex-col transition-all duration-300 relative",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-white/5 justify-between">
        {!collapsed && (
          <span className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-purple-400 tracking-wider text-base">
            MAGOCO EVO
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 hover:bg-white/5 rounded-lg transition-colors text-text-2 hover:text-text-0"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation */}
      <div className="flex-1 px-3 py-4 space-y-1.5">
        <SidebarItem
          icon={MessageSquare}
          label="Agent Chat"
          active={currentTab === "chat"}
          collapsed={collapsed}
          onClick={() => onTabChange("chat")}
        />
        <SidebarItem
          icon={Code}
          label="Coding IDE"
          active={currentTab === "coding"}
          collapsed={collapsed}
          onClick={() => onTabChange("coding")}
        />
        <SidebarItem
          icon={Settings}
          label="Settings"
          active={currentTab === "settings"}
          collapsed={collapsed}
          onClick={() => onTabChange("settings")}
        />
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/5">
        <SidebarItem
          icon={LogOut}
          label="Logout"
          collapsed={collapsed}
          onClick={() => console.log("Logout clicked")}
        />
      </div>
    </div>
  );
}
