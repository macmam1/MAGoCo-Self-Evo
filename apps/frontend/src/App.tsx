import { useCallback, useEffect, useState } from "react";
import {
  LayoutDashboard,
  MessageSquare,
  Code,
  Workflow,
  CheckSquare,
  Link,
  Clock,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { Sidebar } from "@/components/Layout/Sidebar";
import { TopBar } from "@/components/Layout/TopBar";
import { CommandPalette } from "@/components/Layout/CommandPalette";
import { CommandCenter } from "@/components/Dashboard/CommandCenter";
import { ChatConsole } from "@/components/Chat/ChatConsole";
import { CodingIDE } from "@/components/Coding/CodingIDE";
import { WorkflowDesigner } from "@/components/Workflow/WorkflowDesigner";
import { ApprovalGates } from "@/components/Approvals/ApprovalGates";
import { IntegrationsPanel } from "@/components/Integrations/IntegrationsPanel";
import { ExecutionHistory } from "@/components/History/ExecutionHistory";
import { SettingsDashboard } from "@/components/Settings/SettingsDashboard";
import { applyTheme, getTheme } from "@/theme/theme";

export interface AppTab {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
}

const TABS: AppTab[] = [
  { id: "dashboard", label: "Command Center", group: "General", icon: LayoutDashboard },
  { id: "chat", label: "Agent Chat", group: "General", icon: MessageSquare },
  { id: "ide", label: "Coding IDE", group: "General", icon: Code },
  { id: "workflows", label: "Workflows", group: "General", icon: Workflow },
  { id: "approvals", label: "Approvals", group: "Operations", icon: CheckSquare },
  { id: "integrations", label: "Integrations", group: "Operations", icon: Link },
  { id: "history", label: "History", group: "Operations", icon: Clock },
  { id: "settings", label: "Settings", group: "System", icon: Settings },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    applyTheme(getTheme());
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const navigate = useCallback((id: string) => setActiveTab(id), []);

  return (
    <div className="h-screen flex text-gray-100" style={{ background: "var(--app-bg)" }}>
      <Sidebar tabs={TABS} activeTab={activeTab} onTabChange={navigate} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onOpenPalette={() => setPaletteOpen(true)} />
        <main className="flex-1 overflow-hidden">
          {activeTab === "dashboard" && <CommandCenter onNavigate={navigate} />}
          {activeTab === "chat" && <ChatConsole />}
          {activeTab === "ide" && <CodingIDE />}
          {activeTab === "workflows" && <WorkflowDesigner />}
          {activeTab === "approvals" && <ApprovalGates />}
          {activeTab === "integrations" && <IntegrationsPanel />}
          {activeTab === "history" && <ExecutionHistory />}
          {activeTab === "settings" && <SettingsDashboard />}
        </main>
      </div>
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        tabs={TABS}
        onNavigate={navigate}
      />
    </div>
  );
}
