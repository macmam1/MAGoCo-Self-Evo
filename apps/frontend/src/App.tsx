import { useState } from "react";
import { Sidebar } from "@/components/Layout/Sidebar";
import { ChatConsole } from "@/components/Chat/ChatConsole";
import { CodingIDE } from "@/components/Coding/CodingIDE";
import { WorkflowDesigner } from "@/components/Workflow/WorkflowDesigner";
import { ApprovalGates } from "@/components/Approvals/ApprovalGates";
import { IntegrationsPanel } from "@/components/Integrations/IntegrationsPanel";
import { ExecutionHistory } from "@/components/History/ExecutionHistory";
import { SettingsDashboard } from "@/components/Settings/SettingsDashboard";

const TABS = [
  { id: "chat", label: "Agent Chat", icon: "🤖" },
  { id: "ide", label: "Coding IDE", icon: "💻" },
  { id: "workflows", label: "Workflows", icon: "⚡" },
  { id: "approvals", label: "Approvals", icon: "✅" },
  { id: "integrations", label: "Integrations", icon: "🔌" },
  { id: "history", label: "History", icon: "📜" },
  { id: "settings", label: "Settings", icon: "⚙️" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");

  const renderContent = () => {
    switch (activeTab) {
      case "chat": return <ChatConsole />;
      case "ide": return <CodingIDE />;
      case "workflows": return <WorkflowDesigner />;
      case "approvals": return <ApprovalGates />;
      case "integrations": return <IntegrationsPanel />;
      case "history": return <ExecutionHistory />;
      case "settings": return <SettingsDashboard />;
      default: return <ChatConsole />;
    }
  };

  return (
    <div className="h-screen flex bg-gradient-to-b from-[#0a0a1a] to-[#15152a] text-gray-100">
      <Sidebar
        tabs={TABS}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      <main className="flex-1 overflow-hidden">
        {renderContent()}
      </main>
    </div>
  );
}
