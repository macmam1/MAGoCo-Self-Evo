import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import {
  THEMES,
  FONTS,
  applyTheme,
  getTheme,
  applyFont,
  getFont,
  applyDensity,
  getDensity,
  type Density,
} from "@/theme/theme";
import { cn } from "@/lib/utils";

function usePref(key: string, get: () => string) {
  const [val, setVal] = useState(get);
  useEffect(() => {
    const onChange = (e: Event) => setVal((e as CustomEvent<string>).detail ?? get());
    window.addEventListener(key, onChange);
    return () => window.removeEventListener(key, onChange);
  }, [key, get]);
  return [val, setVal] as const;
}

function SectionTitle({ children }: { children: string }) {
  return (
    <div className="text-xs font-semibold mb-2" style={{ color: "var(--text-1)" }}>
      {children}
    </div>
  );
}

export function ThemeSwitcher() {
  const [theme, setTheme] = usePref("magoco:theme", getTheme);
  const [font, setFont] = usePref("magoco:font", getFont);
  const [density, setDensity] = usePref("magoco:density", getDensity);

  return (
    <div className="space-y-5">
      {/* Interface theme incl. System auto (Sand pattern) */}
      <div>
        <SectionTitle>Interface theme</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {THEMES.map((t) => {
            const selected = t.id === theme;
            return (
              <button
                key={t.id}
                onClick={() => {
                  applyTheme(t.id);
                  setTheme(t.id);
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
      </div>

      {/* Typeface (Sand pattern) */}
      <div>
        <SectionTitle>Typeface</SectionTitle>
        <div className="grid grid-cols-3 gap-3">
          {FONTS.map((f) => {
            const selected = f.id === font;
            return (
              <button
                key={f.id}
                onClick={() => {
                  applyFont(f.id);
                  setFont(f.id);
                }}
                className={cn(
                  "rounded-xl border p-3 text-center transition-all",
                  selected
                    ? "border-[var(--accent)] ring-1 ring-[var(--accent)]"
                    : "border-white/10 hover:border-white/25"
                )}
                style={{ background: "var(--bg-1)" }}
              >
                <div className="text-xl" style={{ fontFamily: f.stack, color: "var(--text-0)" }}>
                  {f.sample}
                </div>
                <div className="text-xs mt-1" style={{ color: "var(--text-2)" }}>
                  {f.name}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Sidebar density (Sand pattern) */}
      <div>
        <SectionTitle>Sidebar view</SectionTitle>
        <div className="grid grid-cols-2 gap-3">
          {(["default", "compact"] as Density[]).map((d) => {
            const selected = d === density;
            return (
              <button
                key={d}
                onClick={() => {
                  applyDensity(d);
                  setDensity(d);
                }}
                className={cn(
                  "rounded-xl border p-3 text-sm font-medium capitalize transition-all",
                  selected
                    ? "border-[var(--accent)] ring-1 ring-[var(--accent)]"
                    : "border-white/10 hover:border-white/25"
                )}
                style={{ background: "var(--bg-1)", color: "var(--text-0)" }}
              >
                {d}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
