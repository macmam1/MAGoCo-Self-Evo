import { useEffect, useState } from "react";
import { Plus, Trash2, RefreshCw, CheckCircle, XCircle, KeyRound, Server } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button, Badge } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { API_URL } from "@/config";

interface Provider {
  id: string;
  name: string;
  kind: "ollama-local" | "openai-compatible";
  base_url: string;
  has_key: boolean;
  models: string[];
  default_model: string;
  enabled: boolean;
}

export function ProvidersPanel() {
  const { t } = useTranslation();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; msg: string }>>({});

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/providers/`);
      if (r.ok) setProviders(await r.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProviders(); }, []);

  const autodetect = async () => {
    setLoading(true);
    try {
      await fetch(`${API_URL}/api/v1/providers/autodetect-ollama`, { method: "POST" });
      await fetchProviders();
    } finally {
      setLoading(false);
    }
  };

  const testProvider = async (id: string) => {
    setTesting(id);
    try {
      const r = await fetch(`${API_URL}/api/v1/providers/${id}/test`, { method: "POST" });
      const data = await r.json();
      setTestResults((p) => ({ ...p, [id]: data.ok
        ? { ok: true, msg: `${data.models} models` }
        : { ok: false, msg: data.error || "failed" } }));
      if (data.ok) fetchProviders();
    } finally {
      setTesting(null);
    }
  };

  const fetchModels = async (id: string) => {
    setTesting(id);
    try {
      await fetch(`${API_URL}/api/v1/providers/${id}/fetch-models`, { method: "POST" });
      await fetchProviders();
    } finally {
      setTesting(null);
    }
  };

  const deleteProvider = async (id: string) => {
    await fetch(`${API_URL}/api/v1/providers/${id}`, { method: "DELETE" });
    fetchProviders();
  };

  const toggleEnabled = async (p: Provider) => {
    await fetch(`${API_URL}/api/v1/providers/${p.id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !p.enabled }),
    });
    fetchProviders();
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Button variant="primary" size="sm" onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4 mr-1" />{t("providers.add")}
        </Button>
        <Button variant="outline" size="sm" onClick={autodetect} disabled={loading}>
          <Server className="h-4 w-4 mr-1" />{t("providers.autodetect")}
        </Button>
        <Button variant="ghost" size="sm" onClick={fetchProviders} disabled={loading}>
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>
      </div>

      {providers.length === 0 && !loading && (
        <p className="text-xs text-text-2">{t("providers.empty")}</p>
      )}

      {providers.map((p) => (
        <div key={p.id} className="p-3 rounded-xl border" style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              {p.kind === "ollama-local"
                ? <Server className="h-4 w-4 shrink-0" style={{ color: "var(--accent-2)" }} />
                : <KeyRound className="h-4 w-4 shrink-0" style={{ color: "var(--accent)" }} />}
              <div className="min-w-0">
                <div className="text-sm font-medium truncate" style={{ color: "var(--text-0)" }}>{p.name}</div>
                <div className="text-[10px] truncate text-text-2">{p.base_url || p.kind}</div>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <Badge variant={p.enabled ? "default" : "outline"} className="text-[10px]">
                {p.models.length} {t("providers.models")}
              </Badge>
              {testResults[p.id] && (
                testResults[p.id].ok
                  ? <span className="text-emerald-400 flex items-center gap-1 text-[10px]"><CheckCircle className="h-3.5 w-3.5" />{testResults[p.id].msg}</span>
                  : <span className="text-red-400 flex items-center gap-1 text-[10px]"><XCircle className="h-3.5 w-3.5" />{testResults[p.id].msg}</span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-1 mt-2">
            <Button variant="outline" size="sm" onClick={() => testProvider(p.id)} disabled={testing === p.id}>
              {t("providers.test")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => fetchModels(p.id)} disabled={testing === p.id}>
              <RefreshCw className="h-3.5 w-3.5 mr-1" />{t("providers.fetch_models")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => toggleEnabled(p)}>
              {p.enabled ? t("providers.disable") : t("providers.enable")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => deleteProvider(p.id)} className="text-red-400">
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
          {p.default_model && (
            <div className="text-[10px] mt-1 text-text-2">{t("providers.default")}: {p.default_model}</div>
          )}
        </div>
      ))}

      <AddProviderModal open={showAdd} onClose={() => setShowAdd(false)} onDone={fetchProviders} />
    </div>
  );
}

function AddProviderModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const { t } = useTranslation();
  const [kind, setKind] = useState<"ollama-local" | "openai-compatible">("openai-compatible");
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setError("");
    if (!name.trim() || !baseUrl.trim()) { setError(t("providers.name_url_required")); return; }
    setSaving(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/providers/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(), kind, base_url: baseUrl.trim(),
          api_key: apiKey, models: model.trim() ? [model.trim()] : [],
          default_model: model.trim(),
        }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        setError(e.detail || t("providers.create_failed"));
        return;
      }
      setName(""); setBaseUrl(""); setApiKey(""); setModel("");
      onDone(); onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={open} onClose={onClose} title={t("providers.add_title")} size="md">
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium mb-1">{t("providers.kind")}</label>
          <select value={kind} onChange={(e) => setKind(e.target.value as any)}
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm">
            <option value="openai-compatible">{t("providers.kind_compat")}</option>
            <option value="ollama-local">{t("providers.kind_ollama")}</option>
          </select>
          <p className="text-[10px] text-text-2 mt-1">{t("providers.kind_hint")}</p>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">{t("providers.name_label")}</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Local / My Gateway"
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">{t("providers.base_url")}</label>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={kind === "ollama-local" ? "http://localhost:11434" : "https://api.example.com/v1"}
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">{t("providers.api_key")} {kind === "ollama-local" && <span className="text-text-2">({t("providers.optional")})</span>}</label>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
            placeholder="••••••••"
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono" />
          <p className="text-[10px] text-text-2 mt-1">{t("providers.key_note")}</p>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">{t("providers.model_id")}</label>
          <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="llama3.2 / gpt-4o / provider/model"
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono" />
          <p className="text-[10px] text-text-2 mt-1">{t("providers.model_hint")}</p>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>{t("cancel")}</Button>
          <Button variant="primary" onClick={save} disabled={saving}>{t("save")}</Button>
        </div>
      </div>
    </Modal>
  );
}
