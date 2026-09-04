import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { THEMES, applyTheme, getTheme } from "@/theme/theme";
import { cn } from "@/lib/utils";

export function ThemeSwitcher() {
  const [active, setActive] = useState(getTheme());

  useEffect(() => {
    const onChange = (e: Event) =>
      setActive((e as CustomEvent<string>).detail ?? getTheme());
    window.addEventListener("magoco:theme", onChange);
    return () => window.removeEventListener("magoco:theme", onChange);
  }, []);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {THEMES.map((t) => {
        const selected = t.id === active;
        return (
          <button
            key={t.id}
            onClick={() => {
              applyTheme(t.id);
              setActive(t.id);
            }}
            className={cn(
              "text-left rounded-xl border p-3 transition-all",
              selected
                ? "border-[var(--accent)] ring-1 ring-[var(--accent)]"
                : "border-white/10 hover:border-white/25"
            )}
            style={{ background: "var(--bg-1)" }}
          >
            <div className="flex gap-1.5 mb-2.5">
              {t.preview.map((c) => (
                <span
                  key={c}
                  className="h-8 flex-1 rounded-md border border-black/20"
                  style={{ background: c }}
                />
              ))}
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold" style={{ color: "var(--text-0)" }}>
                  {t.name}
                </div>
                <div className="text-xs" style={{ color: "var(--text-2)" }}>
                  {t.blurb}
                </div>
              </div>
              {selected && <Check size={16} style={{ color: "var(--accent)" }} />}
            </div>
          </button>
        );
      })}
    </div>
  );
}
