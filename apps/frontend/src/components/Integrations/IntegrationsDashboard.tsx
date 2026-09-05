import { useEffect, useState } from "react";
import { Globe, Plug, Webhook, KeyRound, RefreshCw, Download } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button, Badge } from "@/components/ui";
import { API_URL } from "@/config";

type TabId = "marketplace" | "installed" | "webhooks" | "oauth";

export function IntegrationsDashboard() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<TabId>("marketplace");
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");

  const fetchMarket = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/integrations-registry/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, page: 1, page_size: 20 }),
      });
      if (r.ok) setItems(await r.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const seed = async () => {
    setLoading(true);
    try {
      await fetch(`${API_URL}/api/v1/integrations-registry/seed`, { method: "POST" });
      await fetchMarket();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMarket(); }, []);

  const tabs: { id: TabId; label: string; icon: any }[] = [
    { id: "marketplace", label: t("integrations.marketplace", "Marketplace"), icon: Globe },
    { id: "installed", label: t("integrations.installed", "Installed"), icon: Plug },
    { id: "webhooks", label: t("integrations.webhooks", "Webhooks"), icon: Webhook },
    { id: "oauth", label: t("integrations.oauth", "OAuth"), icon: KeyRound },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
            <Plug className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="font-medium text-sm text-white">{t("integrations.title", "Integrations")}</h2>
            <p className="text-xs text-text-2">{t("integrations.subtitle", "OAuth, webhooks, MCP & connectors")}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={seed} disabled={loading}>
            <Download className="h-4 w-4 mr-1" />{t("integrations.seed", "Seed")}
          </Button>
          <Button variant="outline" size="sm" onClick={fetchMarket} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4 mr-1", loading && "animate-spin")} />{t("refresh", "Refresh")}
          </Button>
        </div>
      </div>

      <div className="flex border-b border-white/5 overflow-x-auto">
        {tabs.map((tb) => (
          <button key={tb.id} onClick={() => setTab(tb.id)}
            className={cn("flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2",
              tab === tb.id ? "text-[var(--accent)] border-[var(--accent)]" : "text-text-2 border-transparent")}>
            <tb.icon className="h-4 w-4" />{tb.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === "marketplace" && (
          <div>
            <div className="flex gap-2 mb-4">
              <input value={query} onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && fetchMarket()}
                placeholder={t("integrations.search_placeholder", "Search integrations...")}
                className="flex-1 bg-gray-800/50 border border-white/10 rounded-lg px-4 py-2" />
              <Button size="sm" onClick={fetchMarket}>{t("search", "Search")}</Button>
            </div>
            {loading ? <p className="text-text-2 text-sm">Loading...</p> : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((it: any) => {
                  const m = it.integration || it;
                  return (
                    <div key={m.id} className="p-4 rounded-xl border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                      <div className="font-medium" style={{ color: "var(--text-0)" }}>{m.display_name || m.name}</div>
                      <p className="text-xs text-text-2 line-clamp-2 mt-1">{m.description}</p>
                      <div className="flex items-center justify-between mt-3">
                        <Badge variant="outline" className="text-[10px] capitalize">{m.category}</Badge>
                        <span className="text-[11px] text-text-2">★ {m.rating ?? 0}</span>
                      </div>
                    </div>
                  );
                })}
                {items.length === 0 && <p className="text-text-2 text-sm">No integrations yet — click Seed.</p>}
              </div>
            )}
          </div>
        )}
        {tab === "installed" && <p className="text-sm text-text-2">Installed instances (local) — coming from instance API next.</p>}
        {tab === "webhooks" && <WebhookPanel />}
        {tab === "oauth" && <OAuthPanel />}
      </div>
    </div>
  );
}

function WebhookPanel() {
  const { t } = useTranslation();
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [events, setEvents] = useState("created,updated");
  return (
    <div className="max-w-xl space-y-3">
      <h3 className="font-medium">{t("integrations.webhook_config", "Webhook config")}</h3>
      <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://your-app.com/webhook"
        className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2" />
      <input value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="webhook secret"
        className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2" />
      <input value={events} onChange={(e) => setEvents(e.target.value)} placeholder="created,updated"
        className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2" />
      <p className="text-xs text-text-2">Signature header: X-Signature (HMAC-SHA256). Verify on receipt.</p>
    </div>
  );
}

function OAuthPanel() {
  const { t } = useTranslation();
  const [clientId, setClientId] = useState("");
  const [authUrl, setAuthUrl] = useState("https://provider.com/oauth/authorize");
  const [scope, setScope] = useState("read write");
  const start = () => {
    const redirect = `${window.location.origin}/oauth/callback`;
    const u = `${authUrl}?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(redirect)}&response_type=code&scope=${encodeURIComponent(scope)}&state=magoco-${Date.now()}`;
    window.open(u, "_blank");
  };
  return (
    <div className="max-w-xl space-y-3">
      <h3 className="font-medium">{t("integrations.oauth_helper", "OAuth helper")}</h3>
      <input value={clientId} onChange={(e) => setClientId(e.target.value)} placeholder="client_id"
        className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2" />
      <input value={authUrl} onChange={(e) => setAuthUrl(e.target.value)} placeholder="authorization url"
        className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2" />
      <input value={scope} onChange={(e) => setScope(e.target.value)} placeholder="scopes"
        className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2" />
      <Button size="sm" onClick={start}>Open authorize URL</Button>
    </div>
  );
}
