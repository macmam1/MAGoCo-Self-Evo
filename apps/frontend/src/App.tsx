import { useCallback, useEffect, useRef, useState } from "react";
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
  TrendingUp,
  Target,
  type LucideIcon,
} from "lucide-react";
import { Sidebar } from "@/components/Layout/Sidebar";
import { TopBar } from "@/components/Layout/TopBar";
import { Taskbar } from "@/components/OS/Taskbar";
import { Desktop, type WinState } from "@/components/OS/WindowManager";
import { CommandPalette } from "@/components/Layout/CommandPalette";
import { CommandCenter } from "@/components/Dashboard/CommandCenter";
import { ChatConsole } from "@/components/Chat/ChatConsole";
import { CodingIDE } from "@/components/Coding/CodingIDE";
import { WorkflowDesigner } from "@/components/Workflow/WorkflowDesigner";
import { ApprovalGates } from "@/components/Approvals/ApprovalGates";
import { IntegrationsDashboard } from "@/components/Integrations/IntegrationsDashboard";
import { Processes } from "@/components/History/Processes";
import { SettingsDashboard } from "@/components/Settings/SettingsDashboard";
import { AgentBrowser } from "@/components/Browser/AgentBrowser";
import { SkillsDashboard } from "@/components/Skills/SkillsDashboard";
import { GrowthDashboard } from "@/components/Growth/GrowthDashboard";
import { PlanningPanel } from "@/components/Planning/PlanningPanel";
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
  { id: "dashboard", label: "nav.dashboard", group: "groups.observe", icon: LayoutDashboard },
  { id: "chat", label: "nav.chat", group: "groups.build", icon: MessageSquare },
  { id: "planning", label: "nav.planning", group: "groups.build", icon: Target },
  { id: "ide", label: "nav.ide", group: "groups.build", icon: Code },
  { id: "workflows", label: "nav.workflows", group: "groups.build", icon: Workflow },
  { id: "browser", label: "nav.browser", group: "groups.build", icon: Globe },
  { id: "skills", label: "nav.skills", group: "groups.build", icon: Package },
  { id: "growth", label: "nav.growth", group: "groups.grow", icon: TrendingUp },
  { id: "approvals", label: "nav.approvals", group: "groups.observe", icon: CheckSquare },
  { id: "integrations", label: "nav.integrations", group: "groups.connect", icon: Link },
  { id: "history", label: "nav.history", group: "groups.observe", icon: Clock },
  { id: "settings", label: "nav.settings", group: "groups.system", icon: Settings },
];

export default function App() {
  const [windows, setWindows] = useState<WinState[]>([]);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const zTop = useRef(10);
  const cascade = useRef(0);
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

  const navigate = useCallback(
    (id: string) => {
      const tab = TABS.find((tb) => tb.id === id);
      if (!tab) return;
      setWindows((prev) => {
        const existing = prev.find((w) => w.tabId === id);
        zTop.current += 1;
        if (existing) {
          setFocusedId(existing.winId);
          return prev.map((w) =>
            w.winId === existing.winId ? { ...w, minimized: false, z: zTop.current } : w,
          );
        }
        const n = cascade.current++;
        const dw = Math.max(900, window.innerWidth - 320);
        const dh = Math.max(600, window.innerHeight - 140);
        const w = Math.round(dw * 0.86);
        const h = Math.round(dh * 0.9);
        const winId = `win-${Date.now().toString(36)}-${n}`;
        setFocusedId(winId);
        return [
          ...prev,
          {
            winId,
            tabId: id,
            title: t(tab.label),
            x: 40 + (n % 6) * 36,
            y: 24 + (n % 6) * 28,
            w: Math.min(w, dw),
            h: Math.min(h, dh),
            z: zTop.current,
            minimized: false,
            maximized: false,
          },
        ];
      });
    },
    [t],
  );

  const renderContent = useCallback(
    (tabId: string) => {
      switch (tabId) {
        case "dashboard":
          return <CommandCenter onNavigate={navigate} />;
        case "chat":
          return <ChatConsole />;
        case "planning":
          return <PlanningPanel />;
        case "ide":
          return <CodingIDE />;
        case "workflows":
          return <WorkflowDesigner />;
        case "browser":
          return <AgentBrowser />;
        case "skills":
          return <SkillsDashboard />;
        case "growth":
          return <GrowthDashboard />;
        case "approvals":
          return <ApprovalGates />;
        case "integrations":
          return <IntegrationsDashboard />;
        case "history":
          return <Processes />;
        case "settings":
          return <SettingsDashboard />;
        default:
          return null;
      }
    },
    [navigate],
  );

  const focusWindow = useCallback((winId: string) => {
    zTop.current += 1;
    const z = zTop.current;
    setFocusedId(winId);
    setWindows((prev) => prev.map((w) => (w.winId === winId ? { ...w, z } : w)));
  }, []);

  const onWindowClick = useCallback(
    (winId: string) => {
      const w = windows.find((x) => x.winId === winId);
      if (!w) return;
      if (w.minimized) {
        zTop.current += 1;
        const z = zTop.current;
        setFocusedId(winId);
        setWindows((prev) => prev.map((x) => (x.winId === winId ? { ...x, minimized: false, z } : x)));
      } else if (winId === focusedId) {
        setWindows((prev) => prev.map((x) => (x.winId === winId ? { ...x, minimized: true } : x)));
        const rest = windows.filter((x) => x.winId !== winId && !x.minimized);
        setFocusedId(rest.length > 0 ? rest.sort((a, b) => b.z - a.z)[0].winId : null);
      } else {
        focusWindow(winId);
      }
    },
    [windows, focusedId, focusWindow],
  );

  const updateWindow = useCallback((winId: string, patch: Partial<WinState>) => {
    setWindows((prev) => prev.map((w) => (w.winId === winId ? { ...w, ...patch } : w)));
  }, []);

  const closeWindow = useCallback(
    (winId: string) => {
      setWindows((prev) => {
        const rest = prev.filter((w) => w.winId !== winId);
        if (focusedId === winId) {
          const vis = rest.filter((w) => !w.minimized).sort((a, b) => b.z - a.z);
          setFocusedId(vis.length > 0 ? vis[0].winId : null);
        }
        return rest;
      });
    },
    [focusedId],
  );

  const focusedTab = windows.find((w) => w.winId === focusedId)?.tabId ?? "";

  // Cross-tab navigation events (e.g. Growth "Apply" -> open Skills tab)
  useEffect(() => {
    const onOpenSkill = (e: Event) => {
      navigate("skills");
      try {
        const detail = (e as CustomEvent).detail;
        if (detail?.skill_id) localStorage.setItem("magoco:open-skill", JSON.stringify(detail));
      } catch {}
    };
    const onOpenApprovals = () => navigate("approvals");
    window.addEventListener("magoco:open-skill", onOpenSkill);
    window.addEventListener("magoco:open-approvals", onOpenApprovals);
    return () => {
      window.removeEventListener("magoco:open-skill", onOpenSkill);
      window.removeEventListener("magoco:open-approvals", onOpenApprovals);
    };
  }, [navigate]);

  return (
    <div className="h-screen flex text-gray-100" style={{ background: "var(--app-bg)" }}>
      <Sidebar tabs={tabs} activeTab={focusedTab} onTabChange={navigate} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onOpenPalette={() => setPaletteOpen(true)} />
        <Desktop
          windows={windows}
          focusedId={focusedId}
          renderContent={renderContent}
          onFocus={focusWindow}
          onMove={(id, x, y) => updateWindow(id, { x, y })}
          onResize={(id, w, h) => updateWindow(id, { w, h })}
          onMinimize={(id) => updateWindow(id, { minimized: true })}
          onToggleMax={(id) => {
            const w = windows.find((x) => x.winId === id);
            if (w) updateWindow(id, { maximized: !w.maximized });
          }}
          onClose={closeWindow}
        />
        <Taskbar
          windows={windows}
          focusedId={focusedId}
          onStart={() => setPaletteOpen(true)}
          onWindowClick={onWindowClick}
        />
      </div>
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        tabs={tabs}
        onNavigate={(id) => {
          navigate(id);
          setPaletteOpen(false);
        }}
      />
      <KeyboardShortcutsModal isOpen={showShortcuts} onClose={() => setShowShortcuts(false)} />
    </div>
  );
}
