import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { API_URL } from "@/config";
import { cn } from "@/lib/utils";
import { Button, Badge } from "@/components/ui";

interface TelegramBot {
  bot_id: string;
  name: string;
  mode: string;
  enabled: boolean;
  default_provider_id?: string | null;
  default_model?: string | null;
  allowed_chats: number;
  has_token: boolean;
}

interface TelegramStatus {
  bots: number;
  active_sessions: number;
  polling_bots: number;
  running: boolean;
}

export function TelegramPanel() {
  const { t } = useTranslation();
  const [bots, setBots] = useState<TelegramBot[]>([]);
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [showTest, setShowTest] = useState(false);
  const [testToken, setTestToken] = useState("");
  const [testResult, setTestResult] = useState<any>(null);

  const fetchBots = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/telegram/bots`);
      if (r.ok) setBots(await r.json());
      const s = await fetch(`${API_URL}/api/v1/telegram/status`);
      if (s.ok) setStatus(await s.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBots();
    const interval = setInterval(fetchBots, 10000);
    return () => setInterval(fetchBots, 10000);
  }, [fetchBots]);

  const testBotToken = async () => {
    if (!testToken.trim()) return;
    setTestResult(null);
    try {
      const r = await fetch(`${API_URL}/api/v1/telegram/test-token?token=${encodeURIComponent(testToken)}`, { method: "POST" });
      if (r.ok) setTestResult(await r.json());
    } catch (e) {
      console.error(e);
    }
  };

  const deleteBot = async (bot_id: string) => {
    await fetch(`${API_URL}/api/v1/telegram/bots/${bot_id}`, { method: "DELETE" });
    fetchBots();
  };

  const startAll = async () => {
    await fetch(`${API_URL}/api/v1/telegram/start`, { method: "POST" });
    fetchBots();
  };

  const stopAll = async () => {
    await fetch(`${API_URL}/api/v1/telegram/stop`, { method: "POST" });
    fetchBots();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <h3 className="font-medium text-sm text-white">{t("telegram.title") || "Telegram Gateway"}</h3>
          <Badge variant="outline" className="text-[10px]"><Send size={10} /> {status?.bots || 0} {t("telegram.bots") || "bots"}</Badge>
          <Badge variant={status?.running ? "default" : "outline"} className="text-[10px]">
            {status?.running ? "🟢 Running" : "⚪ Stopped"}
          </Badge>
          <Badge variant="outline" className="text-[10px]">{status?.active_sessions || 0} sessions</Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowTest(true)}>
            {t("telegram.test_token") || "Test Token"}
          </Button>
          {status?.running ? (
            <Button variant="outline" size="sm" onClick={stopAll}>{t("telegram.stop") || "Stop"}</Button>
          ) : (
            <Button variant="primary" size="sm" onClick={startAll}>{t("telegram.start") || "Start"}</Button>
          )}
          <Button variant="primary" size="sm" onClick={() => setShowAdd(true)}>
            <Plus className="h-4 w-4 mr-1" />{t("telegram.add_bot") || "Add Bot"}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && <div className="text-center text-text-2 py-8">Loading...</div>}
        {!loading && bots.length === 0 && (
          <div className="text-center py-8">
            <p className="text-text-2 mb-2">{t("telegram.no_bots") || "No Telegram bots configured"}</p>
            <p className="text-xs text-text-2 mb-4">{t("telegram.no_bots_hint") || "Add a bot with your Telegram token from @BotFather"}</p>
            <Button variant="primary" size="sm" onClick={() => setShowAdd(true)}>
              <Plus className="h-4 w-4 mr-1" />{t("telegram.add_bot") || "Add Bot"}
            </Button>
          </div>
        )}
        {bots.map((bot) => (
          <div key={bot.bot_id} className="p-3 rounded-xl border mb-3" style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center">
                  <Send size={14} className="text-white" />
                </div>
                <div>
                  <div className="font-medium text-sm text-white">{bot.name}</div>
                  <div className="text-[10px] text-text-2">@{bot.bot_id}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={bot.enabled ? "default" : "outline"} className="text-[10px]">
                  {bot.mode}
                </Badge>
                {bot.default_model && (
                  <Badge variant="outline" className="text-[10px]">{bot.default_model}</Badge>
                )}
                <Button variant="ghost" size="sm" onClick={() => deleteBot(bot.bot_id)} className="text-red-400">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            <div className="text-[10px] text-text-2 mt-1">
              {bot.default_provider_id && <span>Provider: {bot.default_provider_id} · </span>}
              {bot.allowed_chats > 0 ? `${bot.allowed_chats} allowed chats` : "All chats allowed"}
            </div>
          </div>
        ))}
      </div>

      <AddBotModal open={showAdd} onClose={() => setShowAdd(false)} onDone={fetchBots} />
      <TestTokenModal open={showTest} onClose={() => setShowTest(false)} />
    </div>
  );
}

function AddBotModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [token, setToken] = useState("");
  const [mode, setMode] = useState("polling");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [defaultProvider, setDefaultProvider] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    if (!name.trim() || !token.trim()) {
      setError(t("telegram.name_token_required") || "Name and token are required");
      return;
    }
    setSaving(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/telegram/bots`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          token: token.trim(),
          mode,
          webhook_url: webhookUrl.trim(),
          default_provider_id: defaultProvider.trim() || undefined,
          default_model: defaultModel.trim() || undefined,
        }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        setError(e.detail || "Creation failed");
        return;
      }
      setName(""); setToken(""); setWebhookUrl(""); setDefaultProvider(""); setDefaultModel("");
      onDone(); onClose();
    } catch (e: any) {
      setError(e.message || "Creation failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={open} onClose={onClose} title={t("telegram.add_bot") || "Add Bot"} size="md">
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium mb-1">{t("telegram.bot_name") || "Bot Name"}</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Assistant Bot"
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">
            {t("telegram.bot_token") || "Bot Token"} <span className="text-text-2">(from @BotFather)</span>
          </label>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="123456789:AAF..."
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">{t("telegram.mode") || "Mode"}</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
          >
            <option value="polling">Polling (recommended)</option>
            <option value="webhook">Webhook</option>
          </select>
        </div>
        {mode === "webhook" && (
          <div>
            <label className="block text-xs font-medium mb-1">{t("telegram.webhook_url") || "Webhook URL"}</label>
            <input
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://your-domain.com/api/v1/telegram/webhook/bot-id"
              className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-medium mb-1">{t("telegram.default_provider") || "Default Provider"}</label>
            <input
              value={defaultProvider}
              onChange={(e) => setDefaultProvider(e.target.value)}
              placeholder="openai"
              className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">{t("telegram.default_model") || "Default Model"}</label>
            <input
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              placeholder="gpt-4o"
              className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={saving}>{t("cancel")}</Button>
          <Button variant="primary" onClick={save} disabled={saving}>{t("save")}</Button>
        </div>
      </div>
    </Modal>
  );
}

function TestTokenModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const [token, setToken] = useState("");
  const [result, setResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  const test = async () => {
    if (!token.trim()) return;
    setTesting(true);
    setResult(null);
    try {
      const r = await fetch(`${API_URL}/api/v1/telegram/test-token?token=${encodeURIComponent(token.trim())}`, { method: "POST" });
      if (r.ok) setResult(await r.json());
    } catch (e) {
      setResult({ valid: false, error: "Network error" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Modal isOpen={open} onClose={onClose} title={t("telegram.test_token") || "Test Token"} size="sm">
      <div className="space-y-3">
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Bot token to test"
          className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
        />
        {result && (
          <div className={cn("p-3 rounded-lg text-sm", result.valid ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400")}>
            {result.valid ? (
              <>
                ✅ Valid! @{result.username}
                <div className="text-xs mt-1">First name: {result.first_name}</div>
              </>
            ) : (
              <>❌ {result.error}</>
            )}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Close</Button>
          <Button variant="primary" onClick={test} disabled={testing || !token.trim()}>
            {testing ? "Testing..." : "Test"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

import { Send, Plus, Trash2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";