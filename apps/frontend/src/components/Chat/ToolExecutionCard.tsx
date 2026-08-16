import { cn } from "@/lib/utils";
import { X, Trash2, Play, CheckCircle2, Circle } from "lucide-react";

export interface ToolExecutionCardProps {
  tool: {
    name: string;
    description?: string;
  };
  args: Record<string, string>;
  result?: {
    success: boolean;
    content?: string;
    error?: string;
    metadata?: Record<string, unknown>;
  };
  onRemove?: () => void;
  expanded?: boolean;
  onToggle?: () => void;
}

export function ToolExecutionCard({
  tool,
  args,
  result,
  onRemove,
  expanded = false,
  onToggle,
}: ToolExecutionCardProps) {
  const allArgs = Object.entries(args);

  return (
    <div className="glass-soft rounded-xl overflow-hidden border border-white/5">
      {/* Header with toggle + remove */}
      <div className="flex items-center justify-between px-3 py-2 bg-white/5">
        <div className="flex items-center space-x-2">
          <span className="font-medium text-xs text-text-0">
            {tool.name}
          </span>
          {result?.success ? (
            <CheckCircle2 size={12} className="text-emerald-400" />
          ) : (
            <Circle size={12} className="text-text-2" />
          )}
        </div>
        <div className="flex items-center space-x-1.5">
          <button
            onClick={onToggle}
            className="p-1 hover:bg-white/10 rounded-lg transition-colors"
          >
            {expanded ? <X size={12} /> : (allArgs.length > 2 ? (<ChevronDown size={12} />) : <span />)}
          </button>
          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1 hover:bg-red-500/10 rounded-lg transition-colors text-text-2 hover:text-red-400"
            >
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Arguments */}
      <div className="px-3 py-2 text-xs space-y-1">
        {allArgs.length > 0 && (
          <div className="space-y-1">
            {allArgs.map(([key, value]) => (
              <div key={key} className="flex items-center space-x-2 text-text-2">
                <span className="font-mono text-text-1">{key}</span>
                <span className="font-mono truncate flex-1">
                  {String(value)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Result - only show when expanded or success + no args */}
      {(expanded || (result?.success && allArgs.length === 0)) &&
        result && (
          <div className="border-t border-white/5 px-3 py-2 text-xs space-y-1">
            {result.success ? (
              result.content && (
                <div className="mb-1">
                  <div className="text-text-2 mb-0.5">Result:</div>
                  <div className="bg-black/30 rounded-lg px-2 py-1 font-mono text-text-0 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                    {result.content}
                  </div>
                </div>
              )
            ) : (
              <div className="text-red-400">
                ❌ {result.error || "Execution failed"}
              </div>
            )}
          </div>
        )}
    </div>
  );
}