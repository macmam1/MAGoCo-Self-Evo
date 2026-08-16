import { useState } from "react";
import { Key, Shield, HardDrive, Cpu, RefreshCw, Save } from "lucide-react";
import { cn } from "@/lib/utils";

interface SettingsCardProps {
  title: string;
  description: string;
  icon: React.ElementType;
  children: React.ReactNode;
}

function SettingsCard({ title, description, icon: Icon, children }: SettingsCardProps) {
  return (
    <div className="glass-soft border border-white/5 rounded-2xl p-6 space-y-4">
      <div className="flex items-center space-x-3">
        <div className="p-2.5 bg-primary-500/10 rounded-xl text-primary-400">
          <Icon size={20} />
        </div>
        <div>
          <h3 className="font-semibold text-text-0 text-sm">{title}</h3>
          <p className="text-text-2 text-xs">{description}</p>
        </div>
      </div>
      <div className="pt-2">{children}</div>
    </div>
  );
}

export function SettingsDashboard() {
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState("sk-proj-....................");

  return (
    <div className="flex-1 overflow-y-auto bg-bg-0 p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-0">System Settings</h1>
        <p className="text-text-2 text-xs mt-1">Configure your LLM providers, dynamic skills, and memory systems.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl">
        {/* API Credentials */}
        <SettingsCard
          title="LLM Providers"
          description="Manage credentials and configurations for OpenAI, Anthropic, Ollama."
          icon={Key}
        >
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-text-1 mb-1.5">OpenAI API Key</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-text-0 focus:outline-none focus:border-primary-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-1 mb-1.5">Ollama Base URL</label>
              <input
                type="text"
                defaultValue="http://localhost:11434"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-text-0 focus:outline-none focus:border-primary-500 transition-colors"
              />
            </div>
          </div>
        </SettingsCard>

        {/* Dynamic Skills */}
        <SettingsCard
          title="Dynamic Skills"
          description="Enable or disable execution modules loaded from SKILL.md templates."
          icon={Cpu}
        >
          <div className="space-y-2">
            {[
              { name: "web_search", desc: "Retrieve live results from search engines", enabled: true },
              { name: "code_executor", desc: "Compile and execute Python code in safe Docker", enabled: true },
              { name: "file_manager", desc: "Read and write working space filesystem", enabled: false },
            ].map((skill) => (
              <div key={skill.name} className="flex items-center justify-between p-2.5 bg-white/5 rounded-xl border border-white/5">
                <div>
                  <span className="font-mono text-xs font-medium text-text-0">{skill.name}</span>
                  <p className="text-[10px] text-text-2">{skill.desc}</p>
                </div>
                <div className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked={skill.enabled}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:height-4 after:width-4 after:transition-all peer-checked:bg-primary-500"></div>
                </div>
              </div>
            ))}
          </div>
        </SettingsCard>

        {/* Memory System */}
        <SettingsCard
          title="3-Layer Memory Inspector"
          description="View and manage context size and knowledge graphs."
          icon={HardDrive}
        >
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div className="p-3 bg-white/5 rounded-xl text-center border border-white/5">
                <span className="block text-[10px] text-text-2 font-medium">Working Context</span>
                <span className="text-sm font-semibold text-primary-400">4 / 50 turns</span>
              </div>
              <div className="p-3 bg-white/5 rounded-xl text-center border border-white/5">
                <span className="block text-[10px] text-text-2 font-medium">Verbatim History</span>
                <span className="text-sm font-semibold text-purple-400">128 turns</span>
              </div>
              <div className="p-3 bg-white/5 rounded-xl text-center border border-white/5">
                <span className="block text-[10px] text-text-2 font-medium">Distilled Facts</span>
                <span className="text-sm font-semibold text-emerald-400">12 rules</span>
              </div>
            </div>
            <button className="w-full flex items-center justify-center space-x-2 py-2 bg-white/5 hover:bg-white/10 text-xs font-medium rounded-xl border border-white/10 transition-colors text-text-1 hover:text-text-0">
              <RefreshCw size={12} />
              <span>Distill & Clear Context</span>
            </button>
          </div>
        </SettingsCard>

        {/* Security Guard */}
        <SettingsCard
          title="Security Sandbox"
          description="Configure Kernel and File Guards to block risky commands."
          icon={Shield}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-text-1">Interactive Command Approval</span>
              <span className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/10 rounded-full font-medium">Enabled</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-text-1">Anti-Evasion Detection Logs</span>
              <span className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/10 rounded-full font-medium">Active</span>
            </div>
          </div>
        </SettingsCard>
      </div>

      {/* Save Button */}
      <div className="max-w-5xl flex justify-end">
        <button className="flex items-center space-x-2 px-5 py-2.5 bg-primary-500 hover:bg-primary-600 active:scale-95 transition-all text-sm font-medium rounded-xl text-white shadow-lg shadow-primary-500/20">
          <Save size={16} />
          <span>Save Changes</span>
        </button>
      </div>
    </div>
  );
}
