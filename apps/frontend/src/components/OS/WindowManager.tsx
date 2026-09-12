import { useCallback, useEffect, useRef, useState } from "react";
import { Minus, Square, X, Copy } from "lucide-react";

export interface WinState {
  winId: string;
  tabId: string;
  title: string;
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  minimized: boolean;
  maximized: boolean;
}

interface DesktopProps {
  windows: WinState[];
  focusedId: string | null;
  renderContent: (tabId: string) => React.ReactNode;
  onFocus: (winId: string) => void;
  onMove: (winId: string, x: number, y: number) => void;
  onResize: (winId: string, w: number, h: number) => void;
  onMinimize: (winId: string) => void;
  onToggleMax: (winId: string) => void;
  onClose: (winId: string) => void;
}

/** OS desktop: draggable / resizable / minimizable overlapping windows. */
export function Desktop(props: DesktopProps) {
  const { windows, focusedId } = props;
  const visible = windows.filter((w) => !w.minimized);
  return (
    <div className="relative flex-1 min-h-0 overflow-hidden" style={{ background: "var(--app-bg)" }}>
      {visible.length === 0 && <EmptyDesktop />}
      {visible.map((w) => (
        <WindowFrame key={w.winId} win={w} focused={w.winId === focusedId} {...props} />
      ))}
    </div>
  );
}

function EmptyDesktop() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 select-none">
      <div className="text-sm font-semibold tracking-tight" style={{ color: "var(--text-1)" }}>
        MAGoCo OS
      </div>
      <div className="text-[11px] mono" style={{ color: "var(--text-2)" }}>
        open a module from the sidebar — or press ⌘K
      </div>
    </div>
  );
}

function WindowFrame({
  win, focused, renderContent, onFocus, onMove, onResize, onMinimize, onToggleMax, onClose,
}: {
  win: WinState;
  focused: boolean;
} & Omit<DesktopProps, "windows" | "focusedId">) {
  const drag = useRef<{ dx: number; dy: number } | null>(null);
  const resize = useRef<{ sw: number; sh: number; sx: number; sy: number } | null>(null);

  const onMouseMove = useCallback(
    (e: MouseEvent) => {
      if (drag.current) {
        onMove(win.winId, e.clientX - drag.current.dx, Math.max(0, e.clientY - drag.current.dy));
      } else if (resize.current) {
        const r = resize.current;
        onResize(win.winId, Math.max(360, r.sw + e.clientX - r.sx), Math.max(240, r.sh + e.clientY - r.sy));
      }
    },
    [win.winId, onMove, onResize],
  );

  useEffect(() => {
    const up = () => {
      drag.current = null;
      resize.current = null;
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", up);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", up);
    };
  }, [onMouseMove]);

  const style: React.CSSProperties = win.maximized
    ? { left: 8, top: 8, right: 8, bottom: 8, zIndex: win.z }
    : { left: win.x, top: win.y, width: win.w, height: win.h, zIndex: win.z };

  return (
    <div
      className="absolute flex flex-col rounded-xl border overflow-hidden"
      style={{
        ...style,
        background: "var(--bg-1)",
        borderColor: focused ? "var(--accent)" : "var(--border-glass)",
        boxShadow: focused ? "0 18px 60px rgba(0,0,0,0.55)" : "0 8px 28px rgba(0,0,0,0.45)",
      }}
      onMouseDown={() => onFocus(win.winId)}
    >
      {/* titlebar */}
      <div
        className="h-9 shrink-0 flex items-center gap-2 px-3 border-b select-none"
        style={{
          borderColor: "var(--border-glass)",
          background: "var(--bg-2)",
          cursor: win.maximized ? "default" : "grab",
        }}
        onMouseDown={(e) => {
          if (win.maximized || (e.target as HTMLElement).closest("button")) return;
          drag.current = { dx: e.clientX - win.x, dy: e.clientY - win.y };
        }}
        onDoubleClick={() => onToggleMax(win.winId)}
      >
        <span className="text-xs font-semibold truncate flex-1" style={{ color: "var(--text-0)" }}>
          {win.title}
        </span>
        <button
          onClick={() => onMinimize(win.winId)}
          className="p-1 rounded hover:bg-white/10"
          title="Minimize"
          style={{ color: "var(--text-2)" }}
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => onToggleMax(win.winId)}
          className="p-1 rounded hover:bg-white/10"
          title="Maximize"
          style={{ color: "var(--text-2)" }}
        >
          {win.maximized ? <Copy className="h-3 w-3" /> : <Square className="h-3 w-3" />}
        </button>
        <button
          onClick={() => onClose(win.winId)}
          className="p-1 rounded hover:bg-red-500/30"
          title="Close"
          style={{ color: "var(--text-2)" }}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      {/* content */}
      <div className="flex-1 min-h-0 overflow-hidden">{renderContent(win.tabId)}</div>
      {/* resize handle */}
      {!win.maximized && (
        <div
          className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize"
          onMouseDown={(e) => {
            e.stopPropagation();
            resize.current = { sw: win.w, sh: win.h, sx: e.clientX, sy: e.clientY };
          }}
        >
          <svg viewBox="0 0 16 16" className="w-4 h-4 opacity-40">
            <path d="M14 14 L14 8 L8 14 Z" fill="var(--text-2)" />
          </svg>
        </div>
      )}
    </div>
  );
}
