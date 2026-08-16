import { useState } from "react";
import { Sidebar } from "@/components/Layout/Sidebar";
import { ChatConsole } from "@/components/Chat/ChatConsole";
import { CodingIDE } from "@/components/Coding/CodingIDE";
import { WorkflowDesigner } from "@/components/Workflow/WorkflowDesigner";
import { SettingsDashboard } from "@/components/Settings/SettingsDashboard";

export default function App() {
  const [currentTab, setCurrentTab] = useState<string>("chat");

  return (
    <div className="flex h-screen w-screen bg-[#0a0a0f] text-slate-100 overflow-hidden font-sans">
      <Sidebar currentTab={currentTab} onTabChange={setCurrentTab} />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {currentTab === "chat" && <ChatConsole />}
        {currentTab === "coding" && <CodingIDE />}
        {currentTab === "workflow" && <WorkflowDesigner />}
        {currentTab === "settings" && <SettingsDashboard />}
      </div>
    </div>
  );
}
