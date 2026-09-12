import { useCallback, useEffect, useRef, useState } from "react";

interface SplitPaneProps {
  left: React.ReactNode;
  right: React.ReactNode;
  showRight: boolean;
  initialRatio?: number;
  minLeft?: number;
  minRight?: number;
}

/** Horizontal split with drag divider. No dependencies. */
export function SplitPane({
  left,
  right,
  showRight,
  initialRatio = 0.62,
  minLeft = 320,
  minRight = 280,
}: SplitPaneProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(initialRatio);
  const dragging = useRef(false);

  const onMove = useCallback(
    (e: MouseEvent) => {
      if (!dragging.current || !ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      let r = (e.clientX - rect.left) / rect.width;
      const minR = minLeft / rect.width;
      const maxR = 1 - minRight / rect.width;
      r = Math.min(maxR, Math.max(minR, r));
      setRatio(r);
    },
    [minLeft, minRight],
  );

  useEffect(() => {
    const up = () => {
      dragging.current = false;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", up);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", up);
    };
  }, [onMove]);

  return (
    <div ref={ref} className="flex h-full w-full min-h-0">
      <div className="min-h-0 min-w-0 flex flex-col" style={{ width: showRight ? `${ratio * 100}%` : "100%" }}>
        {left}
      </div>
      {showRight && (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            onMouseDown={() => {
              dragging.current = true;
            }}
            className="w-1.5 shrink-0 cursor-col-resize transition-colors hover:bg-[var(--accent)]/40"
            style={{ background: "transparent" }}
            title="Drag to resize"
          />
          <div className="min-h-0 min-w-0 flex-1 border-l" style={{ borderColor: "var(--border-glass)" }}>
            {right}
          </div>
        </>
      )}
    </div>
  );
}
