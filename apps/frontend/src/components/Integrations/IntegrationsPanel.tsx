import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, RefreshCw, Link, Unlink } from "lucide-react";

interface ServiceType {
  id: string;
  label: string;
  icon: string;
  color: string;
  connected: boolean;
  connectedAs?: string;
}

const SERVICES: ServiceType[] = [
  { id: "slack", label: "Slack", icon: "💬", color: "#4A154B", connected: false },
  { id: "github", label: "GitHub", icon: "🐙", color: "#333", connected: false },
  { id: "gmail", label: "Gmail", icon: "📧", color: "#D44638", connected: false },
  { id: "notion", label: "Notion", icon: "📝", color: "#fff", connected: false },
  { id: "hubspot", label: "HubSpot", icon: "🟠", color: "#FF7A59", connected: false },
  { id: "asana", label: "Asana", icon: "📋", color: "#F06A6A", connected: false },
  { id: "linear", label: "Linear", icon: "⚡", color: "#5E6AD2", connected: false },
  { id: "jira", label: "Jira", icon: "🔵", color: "#0052CC", connected: false },
  { id: "telegram", label: "Telegram", icon: "✈️", color: "#0088CC", connected: false },
  { id: "discord", label: "Discord", icon: "🎮", color: "#5865F2", connected: false },
  { id: "google_drive", label: "Google Drive", icon: "📂", color: "#4285F4", connected: false },
  { id: "postgres", label: "PostgreSQL", icon: "🐘", color: "#336791", connected: false },
];

function ServiceCard({ service }: { service: ServiceType }) {
  return (
    <div className="glass-card p-4 flex items-center gap-4 hover:border-purple-500/30 transition-all">
      <div className="text-3xl">{service.icon}</div>
      <div className="flex-1">
        <h3 className="text-white font-medium">{service.label}</h3>
        {service.connected ? (
          <div className="flex items-center gap-2 mt-1">
            <Badge className="bg-green-500/10 text-green-300 border-green-500/20 text-xs">
              Connected
            </Badge>
            {service.connectedAs && (
              <span className="text-gray-500 text-xs">{service.connectedAs}</span>
            )}
          </div>
        ) : (
          <p className="text-gray-500 text-xs mt-1">Not connected</p>
        )}
      </div>
      <div className="flex gap-2">
        {service.connected ? (
          <>
            <button className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-lg hover:bg-red-500/10 text-gray-400 hover:text-red-400 transition-colors">
              <Trash2 className="w-4 h-4" />
            </button>
          </>
        ) : (
          <button className="p-2 rounded-lg bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 transition-colors flex items-center gap-1 text-sm">
            <Link className="w-4 h-4" /> Connect
          </button>
        )}
      </div>
    </div>
  );
}

export function IntegrationsPanel() {
  const connected = SERVICES.filter((s) => s.connected);
  const available = SERVICES.filter((s) => !s.connected);

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Integrations</h2>
          <p className="text-gray-500 text-sm mt-1">
            Connect your accounts to third-party services
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 text-sm transition-colors">
          <Plus className="w-4 h-4" /> Custom Integration
        </button>
      </div>

      {connected.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider flex items-center gap-2">
            <Link className="w-3 h-3" /> Connected ({connected.length})
          </h3>
          {connected.map((s) => (
            <ServiceCard key={s.id} service={s} />
          ))}
        </div>
      )}

      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider flex items-center gap-2">
          <Unlink className="w-3 h-3" /> Available ({available.length})
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {available.map((s) => (
            <ServiceCard key={s.id} service={s} />
          ))}
        </div>
      </div>
    </div>
  );
}
