import { useEffect, useState } from "react";
import { LayoutGrid } from "lucide-react";
import { useCommandStats } from "@/hooks/useCommandStats";
import type { WinState } from "./WindowManager";

interface TaskbarProps {
  windows: WinState[];
  focusedId: string | null;
  onStart: () => void;
  onWindowClick: (winId: string) => void;
}

function useClock(): string {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const h = setInterval(() => setNow(new Date()), 20000);
    return () => clearInterval(h);
  }, []);
  return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** OS taskbar: Start | running windows | tray | clock. */
export function Taskbar({ windows, focusedId, onStart, onWindowClick }: TaskbarProps) {
  const s = useCommandStats(15000);
  const clock = useClock();

  const dot = (ok: boolean, warn = false) => (
    <span
      className="w-1.5 h-1.5 rounded-full shrink-0"
      style={{ background: ok ? "#34d399" : warn ? "#f5a524" : "#f87171" }}
    />
  );

  return (
    <footer
      className="h-10 shrink-0 flex items-center gap-2 px-2 border-t"
      style={{ borderColor: "var(--border-glass)", background: "var(--bg-1)" }}
    >
      {/* Start */}
      <button
        onClick={onStart}
        className="h-7 px-3 rounded-lg text-xs font-bold flex items-center gap-1.5 text-white transition-transform hover:scale-[1.03]"
        style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-2))" }}
        title="Start (⌘K)"
      >
        <LayoutGrid className="h-3.5 w-3.5" />
        Start
      </button>

      <div className="w-px h-5" style={{ background: "var(--border-glass)" }} />

      {/* Running windows */}
      <div className="flex-1 flex items-center gap-1.5 overflow-x-auto min-w-0">
        {windows.length === 0 && (
          <span className="text-[11px]" style={{ color: "var(--text-2)" }}>
            no windows — open a module
          </span>
        )}
        {windows.map((w) => {
          const active = w.winId === focusedId && !w.minimized;
          return (
            <button
              key={w.winId}
              onClick={() => onWindowClick(w.winId)}
              className="h-7 max-w-44 px-2.5 rounded-lg text-[11px] font-medium flex items-center gap-1.5 border shrink-0 transition-colors"
              style={{
                borderColor: active ? "var(--accent)" : "var(--border-glass)",
                background: active ? "var(--bg-2)" : "transparent",
                color: w.minimized ? "var(--text-2)" : "var(--text-0)",
              }}
              title={w.title}
            >
              <span
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: w.minimized ? "var(--text-2)" : "#34d399" }}
              />
              <span className="truncate">{w.title}</span>
            </button>
          );
        })}
      </div>

      {/* Tray */}
      <div className="hidden md:flex items-center gap-3 mono text-[11px] shrink-0" style={{ color: "var(--text-2)" }}>
        <span className="flex items-center gap-1.5">
          {dot(s.online)} {s.online ? `${s.providers.length} prov` : "offline"}
        </span>
        <span className="flex items-center gap-1.5">
          {dot(s.online && (s.approvalsPending ?? 1) === 0, (s.approvalsPending ?? 0) > 0)}
          appr {s.approvalsPending ?? "—"}
        </span>
        <span className="flex items-center gap-1.5">
          {dot(s.online && s.deferred.length === 0, s.deferred.length > 0)}
          def {s.online ? s.deferred.length : "—"}
        </span>
      </div>

      <div className="w-px h-5 hidden md:block" style={{ background: "var(--border-glass)" }} />

      {/* Clock */}
      <span className="mono text-[11px] shrink-0 tabular-nums" style={{ color: "var(--text-1)" }}>
        {clock}
      </span>
    </footer>
  );
}
