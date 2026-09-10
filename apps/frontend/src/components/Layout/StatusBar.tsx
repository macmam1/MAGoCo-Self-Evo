import { useCommandStats } from "@/hooks/useCommandStats";

/** Bottom OS status bar — always visible, always live. No mocks. */
export function StatusBar() {
  const s = useCommandStats(15000);

  const dot = (ok: boolean, warn = false) => (
    <span
      className="w-1.5 h-1.5 rounded-full shrink-0"
      style={{ background: ok ? "#34d399" : warn ? "#f5a524" : "#f87171" }}
    />
  );

  const item = "flex items-center gap-1.5 whitespace-nowrap";

  return (
    <footer
      className="h-8 shrink-0 flex items-center gap-4 px-3 border-t mono text-[11px] overflow-x-auto"
      style={{
        borderColor: "var(--border-glass)",
        background: "var(--bg-1)",
        color: "var(--text-2)",
      }}
    >
      <span className={item} style={{ color: "var(--text-1)" }}>
        {dot(s.online)} {s.online ? "online" : "offline"}
      </span>
      <span className={item}>
        {dot(s.online && s.providers.length > 0)}
        {s.online ? `${s.providers.length} providers` : "providers —"}
      </span>
      <span className={item}>
        {dot(s.online && (s.approvalsPending ?? 1) === 0, (s.approvalsPending ?? 0) > 0)}
        approvals {s.approvalsPending ?? "—"}
      </span>
      <span className={item}>
        {dot(s.online && s.deferred.length === 0, s.deferred.length > 0)}
        deferred {s.online ? s.deferred.length : "—"}
      </span>
      <span className={item}>
        {dot(s.online)}
        tools {s.tools ?? "—"}
      </span>
      <span className="flex-1" />
      <span className={item}>
        {s.online && s.chains.length > 0
          ? `last route → ${s.chains[0].final_provider ?? "?"} ${s.chains[0].final_success ? "ok" : "fail"}`
          : "no routes yet"}
      </span>
    </footer>
  );
}
