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
  Globe,
  Package,
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
import { AgentBrowser } from "@/components/Browser/AgentBrowser";
import { SkillsDashboard } from "@/components/Skills/SkillsDashboard";
import { KeyboardShortcutsModal, useKeyboardShortcuts } from "@/components/ui/KeyboardShortcuts";
import { applyAllPreferences, watchSystemTheme, applyLang, getLang } from "@/theme/theme";
import { useTranslation } from "react-i18next";

export interface AppTab {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
}

const TABS: AppTab[] = [
  { id: "dashboard", label: "nav.dashboard", group: "groups.general", icon: LayoutDashboard },
  { id: "chat", label: "nav.chat", group: "groups.general", icon: MessageSquare },
  { id: "ide", label: "nav.ide", group: "groups.general", icon: Code },
  { id: "workflows", label: "nav.workflows", group: "groups.general", icon: Workflow },
  { id: "browser", label: "nav.browser", group: "groups.general", icon: Globe },
  { id: "skills", label: "nav.skills", group: "groups.general", icon: Package },
  { id: "approvals", label: "nav.approvals", group: "groups.operations", icon: CheckSquare },
  { id: "integrations", label: "nav.integrations", group: "groups.operations", icon: Link },
  { id: "history", label: "nav.history", group: "groups.operations", icon: Clock },
  { id: "settings", label: "nav.settings", group: "groups.system", icon: Settings },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { showShortcuts, setShowShortcuts } = useKeyboardShortcuts();

  useEffect(() => {
    applyAllPreferences();
    watchSystemTheme();
  }, []);

  const { t, i18n } = useTranslation();
  useEffect(() => {
    i18n.changeLanguage(applyLang(getLang()));
  }, [i18n]);

  const tabs = TABS.map((tb) => ({ ...tb, label: t(tb.label), group: t(tb.group) }));

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
      <Sidebar tabs={tabs} activeTab={activeTab} onTabChange={navigate} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onOpenPalette={() => setPaletteOpen(true)} />
        <main className="flex-1 overflow-hidden">
          {activeTab === "dashboard" && <CommandCenter onNavigate={navigate} />}
          {activeTab === "chat" && <ChatConsole />}
          {activeTab === "ide" && <CodingIDE />}
          {activeTab === "workflows" && <WorkflowDesigner />}
          {activeTab === "browser" && <AgentBrowser />}
          {activeTab === "skills" && <SkillsDashboard />}
          {activeTab === "approvals" && <ApprovalGates />}
          {activeTab === "integrations" && <IntegrationsPanel />}
          {activeTab === "history" && <ExecutionHistory />}
          {activeTab === "settings" && <SettingsDashboard />}
        </main>
      </div>
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        tabs={tabs}
        onNavigate={navigate}
      />
      <KeyboardShortcutsModal isOpen={showShortcuts} onClose={() => setShowShortcuts(false)} />
    </div>
  );
}
