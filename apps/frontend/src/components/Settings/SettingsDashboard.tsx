import { useEffect, useState } from "react";
import { Key, Shield, HardDrive, Cpu, RefreshCw, Save, Palette, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { ProvidersPanel } from "./ProvidersPanel";
import { GatewayPanel } from "./GatewayPanel";
import { API_URL } from "@/config";

function MemoryStatsBlock() {
  const [stats, setStats] = useState<any>(null);
  useEffect(() => {
    fetch(`${API_URL}/api/v1/memory/stats`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => {});
  }, []);
  const items = [
    { label: "Total memories", value: stats?.total_memories ?? "—", color: "text-primary-400" },
    { label: "Episodic", value: stats?.episodic_count ?? "—", color: "text-purple-400" },
    { label: "KG nodes", value: stats?.kg_nodes ?? "—", color: "text-emerald-400" },
  ];
  return (
    <div className="grid grid-cols-3 gap-2">
      {items.map((s) => (
        <div key={s.label} className="p-3 bg-white/5 rounded-xl text-center border border-white/5">
          <span className="block text-[10px] text-text-2 font-medium">{s.label}</span>
          <span className={`text-sm font-semibold ${s.color}`}>{s.value}</span>
        </div>
      ))}
    </div>
  );
}

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
  return (
    <div className="flex-1 overflow-y-auto bg-bg-0 p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-0">System Settings</h1>
        <p className="text-text-2 text-xs mt-1">Configure your LLM providers, dynamic skills, and memory systems.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl">
        {/* Appearance & Themes */}
        <SettingsCard
          title="Appearance"
          description="Switch themes instantly. New designs arrive here as themes."
          icon={Palette}
        >
          <ThemeSwitcher />
        </SettingsCard>

        {/* Model Providers (BYOM) */}
        <SettingsCard
          title="Model Providers"
          description="Bring your own model: local Ollama or any OpenAI-compatible endpoint. Keys are encrypted."
          icon={Key}
        >
          <ProvidersPanel />
        </SettingsCard>

        {/* Gateway: live costs, rate limits, fallbacks */}
        <SettingsCard
          title="Gateway Monitor"
          description="Live spend, per-provider rate limits, and recent fallback chains."
          icon={Activity}
        >
          <GatewayPanel />
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
          title="Memory System"
          description="Live stats from the unified memory store (semantic, episodic, KG, RAG)."
          icon={HardDrive}
        >
          <MemoryStatsBlock />
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
