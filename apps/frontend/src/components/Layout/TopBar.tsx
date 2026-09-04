import { useState } from "react";
import { Search, ChevronDown, Languages } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useBackendStatus } from "@/hooks/useBackendStatus";
import { applyLang, getLang } from "@/theme/theme";

export function TopBar({ onOpenPalette }: { onOpenPalette: () => void }) {
  const backend = useBackendStatus();
  const { t, i18n } = useTranslation();
  const [lang, setLang] = useState(getLang());

  const toggleLang = () => {
    const next = lang === "fa" ? "en" : "fa";
    i18n.changeLanguage(applyLang(next));
    setLang(next);
  };

  return (
    <header
      className="h-12 shrink-0 flex items-center gap-3 px-4 border-b"
      style={{ borderColor: "var(--border-glass)", background: "var(--bg-1)" }}
    >
      {/* Cmd+K trigger */}
      <button
        onClick={onOpenPalette}
        className="flex items-center gap-2 text-xs rounded-lg border px-3 py-1.5 w-64 transition-colors hover:border-[var(--accent)]"
        style={{
          background: "var(--bg-2)",
          borderColor: "var(--border-glass)",
          color: "var(--text-2)",
        }}
      >
        <Search className="h-3.5 w-3.5" />
        <span className="flex-1 text-left">{t("topbar.search")}</span>
        <kbd
          className="text-[10px] px-1.5 py-0.5 rounded border"
          style={{ borderColor: "var(--border-glass)" }}
        >
          ⌘K
        </kbd>
      </button>

      <div className="flex-1" />

      {/* Model pill */}
      <span
        className="text-[11px] font-medium px-2.5 py-1 rounded-full border hidden sm:inline-flex items-center gap-1.5"
        style={{
          background: "var(--bg-2)",
          borderColor: "var(--border-glass)",
          color: "var(--text-1)",
        }}
      >
        9Router · Auto <ChevronDown className="h-3 w-3" />
      </span>

      {/* Backend status */}
      <span
        className="inline-flex items-center gap-1.5 text-[11px] font-medium"
        style={{ color: backend.online ? "#34d399" : "#f87171" }}
        title={backend.version ? `v${backend.version} · ${backend.tools} tools` : "unreachable"}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: backend.online ? "#34d399" : "#f87171" }}
        />
        {backend.online ? "Backend" : "Offline"}
      </span>

      {/* Language toggle */}
      <button
        onClick={toggleLang}
        title={lang === "fa" ? "Switch to English" : "تغییر به فارسی"}
        className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-lg border transition-colors hover:border-[var(--accent)]"
        style={{
          background: "var(--bg-2)",
          borderColor: "var(--border-glass)",
          color: "var(--text-1)",
        }}
      >
        <Languages className="h-3.5 w-3.5" />
        {lang === "fa" ? "FA" : "EN"}
      </button>

      {/* User */}
      <div
        className="h-7 w-7 rounded-full flex items-center justify-center text-[11px] font-bold text-white"
        style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-2))" }}
      >
        O
      </div>
    </header>
  );
}
