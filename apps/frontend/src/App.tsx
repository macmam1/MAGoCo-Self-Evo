import { useState } from "react";
import { Sidebar } from "@/components/Layout/Sidebar";
import { ChatConsole } from "@/components/Chat/ChatConsole";
import { SettingsDashboard } from "@/components/Settings/SettingsDashboard";
import { CodingIDE } from "@/components/Coding/CodingIDE";

function App() {
  const [currentTab, setCurrentTab] = useState("chat");

  return (
    <div className="flex h-screen bg-bg-0 text-text-0 overflow-hidden">
      {/* Universal Sidebar */}
      <Sidebar currentTab={currentTab} onTabChange={setCurrentTab} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {currentTab === "chat" && <ChatConsole />}
        {currentTab === "coding" && <CodingIDE />}
        {currentTab === "settings" && <SettingsDashboard />}
      </div>
    </div>
  );
}

export default App;
