import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Send, Bot, User, ChevronDown, ChevronUp, Mic, Paperclip, Brain, Edit, GitBranch, RotateCcw, MoreHorizontal, Trash2, Zap } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useWebSocket } from "@/hooks/useWebSocket";
import { WS_CHAT_URL, API_URL } from "@/config";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ArtifactsPanel, Artifact } from "./ArtifactsPanel";

export function ChatConsole() {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showArtifacts, setShowArtifacts] = useState(false);

  const { messages, isThinking, connect, sendMessage, isConnected } =
    useWebSocket(WS_CHAT_URL);

  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});
  const [streamingThinking, setStreamingThinking] = useState<Record<string, string>>({});
  const [streamingAnswer, setStreamingAnswer] = useState<Record<string, string>>({});
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editInput, setEditInput] = useState("");
  const [showMessageMenu, setShowMessageMenu] = useState<string | null>(null);
  const [selected, setSelected] = useState<{ provider_id: string | null; model: string | null; label: string }>({
    provider_id: null, model: null, label: "Auto",
  });
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [providers, setProviders] = useState<any[]>([]);

  useEffect(() => {
    connect();
    return () => {};
  }, [connect]);

  const fetchProviders = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/v1/providers/`);
      if (r.ok) setProviders(await r.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  useEffect(() => {
    if (showModelMenu) fetchProviders();
  }, [showModelMenu, fetchProviders]);

  const modelOptions = useMemo(() => {
    const opts: { id: string; provider_id: string | null; model: string | null; name: string; desc: string; icon: any }[] = [
      { id: "auto", provider_id: null, model: null, name: "Auto", icon: Zap, desc: "Auto-select best configured provider" },
    ];
    for (const p of providers) {
      if (!p.enabled) continue;
      const models = p.models?.length ? p.models : (p.default_model ? [p.default_model] : []);
      for (const m of models) {
        opts.push({
          id: `${p.id}::${m}`, provider_id: p.id, model: m,
          name: m, icon: p.kind === "ollama-local" ? Zap : Brain, desc: p.name,
        });
      }
    }
    return opts;
  }, [providers]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  const sendChat = useCallback((text: string) => {
    sendMessage(text, { provider_id: selected.provider_id, model: selected.model });
  }, [sendMessage, selected]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !isConnected) return;
    sendChat(trimmed);
    setInput("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleThinking = useCallback((msgId: string) => {
    setExpandedThinking((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  }, []);

  const startEditing = useCallback((msgId: string, content: string) => {
    setEditingMessageId(msgId);
    setEditInput(content);
    setShowMessageMenu(null);
  }, []);

  const saveEdit = useCallback(() => {
    if (!editingMessageId || !editInput.trim()) return;
    sendChat(editInput);
    setEditingMessageId(null);
    setEditInput("");
  }, [editingMessageId, editInput, sendChat]);

  const cancelEdit = useCallback(() => {
    setEditingMessageId(null);
    setEditInput("");
  }, []);

  const forkMessage = useCallback((msgId: string, content: string) => {
    sendChat(content);
    setShowMessageMenu(null);
  }, [sendChat]);

  const resubmitMessage = useCallback((msgId: string, content: string) => {
    sendChat(content);
    setShowMessageMenu(null);
  }, [sendChat]);

  const deleteMessage = useCallback((msgId: string) => {
    setShowMessageMenu(null);
  }, []);

  // Close message menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (showMessageMenu && !(e.target as HTMLElement).closest('[data-message-menu]')) {
        setShowMessageMenu(null);
      }
      if (showModelMenu && !(e.target as HTMLElement).closest('[data-model-menu]')) {
        setShowModelMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showMessageMenu, showModelMenu]);

  // Simulate streaming thinking tokens for demo
  useEffect(() => {
    if (!isThinking) return;
    
    // Find the last assistant message that's being streamed
    const streamingMsg = messages.findLast((m) => m.role === "assistant" && !m.content);
    if (!streamingMsg) return;

    const interval = setInterval(() => {
      setStreamingThinking((prev) => ({
        ...prev,
        [streamingMsg.id]: prev[streamingMsg.id] + "▊",
      }));
    }, 50);

    return () => clearInterval(interval);
  }, [isThinking, messages]);

  // Extract artifacts from messages (code blocks, images, etc.)
  useEffect(() => {
    const extracted: Artifact[] = [];
    let artifactCounter = 0;

    messages.forEach((msg) => {
      if (msg.role !== "assistant") return;
      
      // Extract code blocks
      const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
      let match;
      while ((match = codeBlockRegex.exec(msg.content)) !== null) {
        const language = match[1] || "text";
        const content = match[2].trim();
        if (content) {
          extracted.push({
            id: `artifact-${msg.id}-${artifactCounter++}`,
            type: language === "html" ? "html" : "code",
            title: `Code: ${language}`,
            content,
            language,
            createdAt: Date.now(),
            messageId: msg.id,
          });
        }
      }

      // Extract image URLs
      const imageRegex = /!\[([^\]]*)\]\((https?:\/\/[^)]+)\)/g;
      let imgMatch;
      while ((imgMatch = imageRegex.exec(msg.content)) !== null) {
        const alt = imgMatch[1];
        const url = imgMatch[2];
        extracted.push({
          id: `artifact-${msg.id}-${artifactCounter++}`,
          type: "image",
          title: alt || `Image ${artifactCounter}`,
          content: url,
          createdAt: Date.now(),
          messageId: msg.id,
        });
      }
    });

    if (extracted.length > 0) {
      setArtifacts((prev) => {
        // Merge with existing, avoiding duplicates
        const existingIds = new Set(prev.map((a) => a.id));
        const newArtifacts = extracted.filter((a) => !existingIds.has(a.id));
        return [...prev, ...newArtifacts];
      });
      if (!showArtifacts) setShowArtifacts(true);
    }
  }, [messages, showArtifacts]);

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

        {/* Model Selector */}
        <div className="relative hidden sm:inline-block">
          <button
            onClick={() => setShowModelMenu(!showModelMenu)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium transition-colors hover:border-[var(--accent)]"
            style={{
              background: "var(--bg-2)",
              borderColor: "var(--border-glass)",
              color: "var(--text-1)",
            }}
          >
            <Zap className="h-3.5 w-3.5" style={{ color: "var(--accent)" }} />
            <span>{selected.label}</span>
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", showModelMenu && "rotate-180")} />
          </button>

          {showModelMenu && (
            <div className="absolute right-0 top-full mt-1 z-20 glass-strong rounded-xl border p-1 animate-slide-down min-w-[200px] max-h-80 overflow-y-auto"
                 style={{ borderColor: "var(--border-glass)", background: "var(--bg-1)" }}>
              {modelOptions.map((model) => {
                const Icon = model.icon;
                const active = selected.provider_id === model.provider_id && selected.model === model.model;
                return (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelected({ provider_id: model.provider_id, model: model.model, label: model.id === "auto" ? "Auto" : model.name });
                      setShowModelMenu(false);
                    }}
                    className={cn(
                      "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors",
                      active
                        ? "bg-primary/20 text-primary"
                        : "text-text-1 hover:bg-white/[0.03] hover:text-text-0"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" style={{ color: "var(--accent)" }} />
                    <div className="flex-1 text-left">
                      <div className="font-medium truncate" style={{ color: "var(--text-0)" }}>
                        {model.name}
                      </div>
                      <div className="text-[10px] truncate" style={{ color: "var(--text-2)" }}>
                        {model.desc}
                      </div>
                    </div>
                    {active && (
                      <span className="text-[10px]" style={{ color: "var(--accent)" }}>
                        ✓
                      </span>
                    )}
                  </button>
                );
              })}
              {modelOptions.length <= 1 && (
                <div className="px-3 py-2 text-[11px] text-text-2">
                  {t("chat.no_providers_hint")}
                </div>
              )}
            </div>
          )}
        </div>
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
              {t("hero.greeting")}
            </h3>
            <p className="text-sm mt-1 mb-6" style={{ color: "var(--text-2)" }}>
              {t("hero.sub")}
            </p>

            {/* Example composer → fills the real input */}
            <button
              onClick={() =>
                setInput("Summarise my last agent run and suggest next steps")
              }
              className="w-full text-left rounded-2xl border p-4 mb-3 transition-colors hover:border-[var(--accent)]"
              style={{
                background: "var(--bg-1)",
                borderColor: "var(--border-glass)",
                boxShadow: "var(--shadow-card)",
              }}
            >
              <span className="text-sm block" style={{ color: "var(--text-2)" }}>
                {t("hero.example")}
              </span>
              <span className="flex items-center gap-3 mt-3" style={{ color: "var(--text-2)" }}>
                <Paperclip className="h-4 w-4" />
                <Mic className="h-4 w-4" />
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
                {t("hero.previous")} (128)
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
              <div className="flex justify-end relative">
                {/* Message Menu */}
                {showMessageMenu === msg.id && (
                  <div className="absolute right-full top-0 mr-2 z-10 glass-strong rounded-xl border p-1 animate-slide-right"
                       style={{ borderColor: "var(--border-glass)", background: "var(--bg-1)" }}>
                    <button
                      onClick={() => startEditing(msg.id, msg.content)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-white/[0.05]"
                      style={{ color: "var(--text-0)" }}
                    >
                      <Edit className="h-4 w-4" style={{ color: "var(--accent)" }} />
                      {t("message_actions.edit")}
                    </button>
                    <button
                      onClick={() => forkMessage(msg.id, msg.content)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-white/[0.05]"
                      style={{ color: "var(--text-0)" }}
                    >
                      <GitBranch className="h-4 w-4" style={{ color: "var(--accent-2)" }} />
                      {t("message_actions.fork")}
                    </button>
                    <button
                      onClick={() => resubmitMessage(msg.id, msg.content)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-white/[0.05]"
                      style={{ color: "var(--text-0)" }}
                    >
                      <RotateCcw className="h-4 w-4" style={{ color: "var(--accent-3)" }} />
                      {t("message_actions.resubmit")}
                    </button>
                    <button
                      onClick={() => deleteMessage(msg.id)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-red-500/10 text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                      {t("message_actions.delete")}
                    </button>
                  </div>
                )}
                {/* Edit Mode */}
                {editingMessageId === msg.id ? (
                  <div className="max-w-[80%] glass-strong rounded-2xl rounded-tr-none px-4 py-3 border border-accent/30 animate-slide-down">
                    <div className="flex gap-2">
                      <textarea
                        value={editInput}
                        onChange={(e) => setEditInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            saveEdit();
                          } else if (e.key === "Escape") {
                            cancelEdit();
                          }
                        }}
                        className="flex-1 bg-transparent border-none outline-none resize-none text-sm text-text-0 placeholder:text-text-2 min-h-[40px] max-h-60"
                        rows={2}
                        autoFocus
                        placeholder={t("message_actions.edit_placeholder")}
                      />
                      <div className="flex flex-col gap-1">
                        <Button size="sm" onClick={saveEdit} variant="primary">
                          {t("message_actions.save")}
                        </Button>
                        <Button size="sm" onClick={cancelEdit} variant="ghost">
                          {t("message_actions.cancel")}
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-[80%] bg-white/5 border border-white/10 rounded-2xl rounded-tr-none px-4 py-2.5 relative">
                    <p className="text-sm text-text-0 whitespace-pre-wrap break-words">
                      {msg.content}
                    </p>
                    {/* Message menu trigger */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowMessageMenu(showMessageMenu === msg.id ? null : msg.id);
                      }}
                      className="absolute -top-2 -right-2 h-6 w-6 rounded-full opacity-0 hover:opacity-100 transition-opacity glass-strong flex items-center justify-center"
                      style={{ borderColor: "var(--border-glass)", background: "var(--bg-1)" }}
                    >
                      <MoreHorizontal className="h-3.5 w-3.5" style={{ color: "var(--text-2)" }} />
                    </button>
                  </div>
                )}
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center mr-2">
                  <User size={14} />
                </div>

            {/* Assistant bubble with streaming thinking */}
            {(msg.role === "assistant" || msg.role === "status") && (
              <div className="flex items-start space-x-3">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0">
                  <Bot size={14} />
                </div>
                <div className="max-w-[80%] space-y-2">
                  {/* Streaming Thinking Block */}
                  {(msg.thinking || streamingThinking[msg.id] || isThinking) && (
                    <div className="glass-soft rounded-xl p-3 border border-white/5 transition-all duration-200">
                      <button
                        onClick={() => toggleThinking(msg.id)}
                        className="flex items-center space-x-2 text-xs text-text-2 hover:text-text-0 transition-colors w-full"
                      >
                        <Brain className="h-3.5 w-3.5" style={{ color: "var(--accent-2)" }} />
                        <span>{t("thinking.thinking_process")}</span>
                        {expandedThinking[msg.id] ? (
                          <ChevronUp size={12} />
                        ) : (
                          <ChevronDown size={12} />
                        )}
                        {(streamingThinking[msg.id] || isThinking) && (
                          <span className="ml-auto text-[10px] animate-pulse" style={{ color: "var(--accent-2)" }}>
                            {t("thinking.streaming")}
                          </span>
                        )}
                      </button>

                      {expandedThinking[msg.id] && (
                        <div className="mt-2 text-xs text-text-2 whitespace-pre-wrap break-words font-mono">
                          {streamingThinking[msg.id] || msg.thinking || t("thinking.thinking_placeholder")}
                          {(streamingThinking[msg.id] || isThinking) && (
                            <span className="animate-pulse" style={{ color: "var(--accent)" }}>▊</span>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Answer with streaming */}
                  <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-none px-4 py-3 relative">
                    {streamingAnswer[msg.id] && (
                      <div className="absolute inset-0 bg-black/10 rounded-2xl rounded-bl-none pointer-events-none" />
                    )}
                    <p className="text-sm text-text-0 whitespace-pre-wrap break-words relative z-10">
                      {streamingAnswer[msg.id] || msg.content || t("thinking.generating_answer")}
                      {streamingAnswer[msg.id] && <span className="animate-pulse" style={{ color: "var(--accent)" }}>▊</span>}
                    </p>
                    {!msg.content && !streamingAnswer[msg.id] && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="flex items-center space-x-1">
                          <span className="w-1.5 h-1.5 bg-accent rounded-full thinking-dot" />
                          <span className="w-1.5 h-1.5 bg-accent-2 rounded-full thinking-dot" style={{ animationDelay: "0.2s" }} />
                          <span className="w-1.5 h-1.5 bg-accent-3 rounded-full thinking-dot" style={{ animationDelay: "0.4s" }} />
                        </div>
                      </div>
                    )}
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

      {/* Artifacts Panel */}
      <ArtifactsPanel
        artifacts={artifacts}
        isOpen={showArtifacts}
        onClose={() => setShowArtifacts(false)}
        onCopy={(content) => {
          navigator.clipboard.writeText(content);
        }}
        onDownload={(artifact) => {
          const blob = new Blob([artifact.content], { 
            type: artifact.type === "code" ? "text/plain" : 
                  artifact.type === "html" ? "text/html" : 
                  artifact.type === "image" ? "image/*" : "text/plain" 
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${artifact.title.replace(/\s+/g, "_")}.${artifact.language || "txt"}`;
          a.click();
          URL.revokeObjectURL(url);
        }}
      />
    </div>
  );
}
