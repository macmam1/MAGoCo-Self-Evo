import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, ChevronDown, ChevronUp } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function ChatConsole() {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { messages, isThinking, connect, sendMessage, isConnected } =
    useWebSocket("ws://localhost:8000/ws/chat");

  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});

  useEffect(() => {
    connect();
    return () => {};
  }, [connect]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !isConnected) return;
    sendMessage(trimmed);
    setInput("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleThinking = (msgId: string) => {
    setExpandedThinking((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  return (
    <div className="flex flex-col h-full glass-soft overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center">
            <Bot size={16} />
          </div>
          <div>
            <h2 className="font-medium text-sm text-white">مگوکو هوش مصنوعی</h2>
            <p className="text-xs text-text-2">
              {isConnected ? "متصل به بک‌اند" : "اتصال برقرار نشده"}
            </p>
          </div>
        </div>
        <Badge
          variant={isConnected ? "default" : "destructive"}
          className={cn(
            "text-xs",
            isConnected
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : "bg-red-500/10 text-red-400 border-red-500/20",
          )}
        >
          {isConnected ? "Online" : "Offline"}
        </Badge>
        <span
          className="text-[11px] font-medium px-2.5 py-1 rounded-full border hidden sm:inline-block"
          style={{
            background: "var(--bg-2)",
            borderColor: "var(--border-glass)",
            color: "var(--text-1)",
          }}
        >
          9Router · Auto ▾
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center h-full overflow-y-auto px-6 py-10 max-w-3xl w-full mx-auto">
            {/* Greeting hero (Ask Rune pattern) */}
            <h3
              className="text-2xl font-semibold text-center"
              style={{ color: "var(--text-0)" }}
            >
              Good evening, Operator
            </h3>
            <p className="text-sm mt-1 mb-6" style={{ color: "var(--text-2)" }}>
              I'm Rune, where should we start today?
            </p>

            {/* Example composer → fills the real input */}
            <button
              onClick={() =>
                setInput("Summarise my last agent run and suggest next steps")
              }
              className="w-full text-left rounded-2xl border p-4 mb-3 transition-colors hover:border-[var(--accent)]"
              style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
            >
              <span className="text-sm" style={{ color: "var(--text-2)" }}>
                Example: Summarise my last agent run and suggest next steps…
              </span>
            </button>

            {/* Suggestion chips */}
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {[
                "✉️ Draft a workflow",
                "🔍 Review this repo",
                "🛠️ Explain an error",
                "📝 New skill idea",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s.replace(/^[^\s]+\s/, ""))}
                  className="text-xs px-3 py-1.5 rounded-full border transition-colors hover:border-[var(--accent)]"
                  style={{
                    background: "var(--bg-1)",
                    borderColor: "var(--border-glass)",
                    color: "var(--text-1)",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Previous chats (Finley-card pattern, mock for now) */}
            <div className="w-full">
              <div className="text-xs font-semibold mb-2" style={{ color: "var(--text-2)" }}>
                Previous chats (128)
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[
                  ["Q3 agent performance review", "2h ago"],
                  ["Debug workflow timeout", "Yesterday"],
                  ["Plan v2 UI theme", "2d ago"],
                ].map(([title, when]) => (
                  <div
                    key={title}
                    className="rounded-xl border p-3"
                    style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
                  >
                    <div className="text-xs font-medium truncate" style={{ color: "var(--text-0)" }}>
                      {title}
                    </div>
                    <div className="text-[10px] mt-1" style={{ color: "var(--text-2)" }}>
                      {when}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className="space-y-3">
            {/* User bubble */}
            {msg.role === "user" && (
              <div className="flex justify-end">
                <div className="max-w-[80%] bg-white/5 border border-white/10 rounded-2xl rounded-tr-none px-4 py-2.5">
                  <p className="text-sm text-text-0 whitespace-pre-wrap break-words">
                    {msg.content}
                  </p>
                </div>
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center mr-2">
                  <User size={14} />
                </div>
              </div>
            )}

            {/* Assistant bubble with thinking */}
            {(msg.role === "assistant" || msg.role === "status") && (
              <div className="flex items-start space-x-3">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0">
                  <Bot size={14} />
                </div>
                <div className="max-w-[80%] space-y-2">
                  {/* Thinking block */}
                  <div className="glass-soft rounded-xl p-3 border border-white/5">
                    <button
                      onClick={() => toggleThinking(msg.id)}
                      className="flex items-center space-x-2 text-xs text-text-2 hover:text-text-0 transition-colors w-full"
                    >
                      <span>🤔 در حال فکر کردن</span>
                      {expandedThinking[msg.id] ? (
                        <ChevronUp size={12} />
                      ) : (
                        <ChevronDown size={12} />
                      )}
                    </button>

                    {expandedThinking[msg.id] && msg.thinking && (
                      <div className="mt-2 text-xs text-text-2 whitespace-pre-wrap break-words">
                        {msg.thinking}
                      </div>
                    )}
                  </div>

                  {/* Answer */}
                  <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-none px-4 py-3">
                    <p className="text-sm text-text-0 whitespace-pre-wrap break-words">
                      {msg.content}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Error */}
            {msg.role === "error" && (
              <div className="flex items-start space-x-3">
                <div className="w-7 h-7 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-red-400 text-xs">!</span>
                </div>
                <div className="max-w-[80%] bg-red-900/20 border border-red-500/20 rounded-2xl px-4 py-3">
                  <p className="text-sm text-red-300">{msg.content}</p>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Thinking indicator */}
        {isThinking && (
          <div className="flex items-start space-x-3">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0">
              <Bot size={14} />
            </div>
            <div className="glass-soft rounded-xl px-4 py-3">
              <div className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 bg-accent rounded-full thinking-dot"></span>
                <span className="w-1.5 h-1.5 bg-accent-2 rounded-full thinking-dot" style={{ animationDelay: "0.2s" }}></span>
                <span className="w-1.5 h-1.5 bg-accent-3 rounded-full thinking-dot" style={{ animationDelay: "0.4s" }}></span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/5">
        <div className="glass rounded-xl p-3 border border-white/10 focus-within:border-accent/50 transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="پیام خود را وارد کنید..."
            className="w-full bg-transparent border-none outline-none resize-none text-sm text-text-0 placeholder:text-text-2 min-h-[40px] max-h-32"
            rows={1}
            disabled={!isConnected}
          />
          <div className="flex justify-between items-center mt-2">
            <div className="text-xs text-text-2">
              {isConnected
                ? "فشار دادن Enter برای ارسال،Shift+Enter برای خط جدید"
                : "در حال اتصال..."}
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || !isConnected}
              className={cn(
                "p-2 rounded-lg transition-all duration-200",
                "bg-gradient-to-r from-accent to-accent-2 text-black",
                "hover:shadow-lg hover:scale-105",
                "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
              )}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
