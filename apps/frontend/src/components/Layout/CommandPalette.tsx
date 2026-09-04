import { useEffect, useMemo, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { THEMES, applyTheme } from "@/theme/theme";
import { API_URL } from "@/config";

export interface PaletteTab {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
}

export function CommandPalette({
  open,
  onClose,
  tabs,
  onNavigate,
}: {
  open: boolean;
  onClose: () => void;
  tabs: PaletteTab[];
  onNavigate: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    const nav = tabs.map((t) => ({
      key: `go:${t.id}`,
      title: `Go to ${t.label}`,
      hint: t.group,
      icon: t.icon,
      run: () => onNavigate(t.id),
    }));
    const themes = THEMES.map((t) => ({
      key: `theme:${t.id}`,
      title: `Theme: ${t.name}`,
      hint: "Appearance",
      icon: tabs[0]?.icon,
      run: () => applyTheme(t.id),
    }));
    const docs = [
      {
        key: "open:api-docs",
        title: "Open API docs",
        hint: "Backend",
        icon: tabs[0]?.icon,
        run: () => window.open(`${API_URL}/docs`, "_blank"),
      },
    ];
    const all = [...nav, ...themes, ...docs];
    if (!q) return all;
    return all.filter((i) => (i.title + " " + i.hint).toLowerCase().includes(q));
  }, [query, tabs, onNavigate]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setIndex(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open ]);

  useEffect(() => setIndex(0), [query]);

  if (!open) return null;

  const run = (i: number) => {
    items[i]?.run();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] p-4"
      style={{ background: "rgba(0,0,0,0.55)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border overflow-hidden shadow-2xl"
        style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setIndex((i) => Math.min(i + 1, items.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setIndex((i) => Math.max(i - 1, 0));
            } else if (e.key === "Enter") {
              run(index);
            } else if (e.key === "Escape") {
              onClose();
            }
          }}
          placeholder="Type a command or search…"
          className="w-full bg-transparent outline-none px-4 py-3.5 text-sm"
          style={{ color: "var(--text-0)" }}
        />
        <div className="max-h-72 overflow-y-auto p-2 border-t" style={{ borderColor: "var(--border-glass)" }}>
          {items.length === 0 && (
            <div className="px-3 py-6 text-center text-xs" style={{ color: "var(--text-2)" }}>
              No results
            </div>
          )}
          {items.map((item, i) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                onClick={() => run(i)}
                onMouseEnter={() => setIndex(i)}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm"
                style={
                  i === index
                    ? { background: "var(--bg-2)", color: "var(--text-0)" }
                    : { color: "var(--text-1)" }
                }
              >
                {Icon && <Icon className="h-4 w-4 shrink-0" />}
                <span className="flex-1 text-left">{item.title}</span>
                <span className="text-[10px]" style={{ color: "var(--text-2)" }}>
                  {item.hint}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
