import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Mic, Paperclip, ArrowRight, AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useWebSocket } from "@/hooks/useWebSocket";
import { WS_AGENT_BROWSER_URL } from "@/config";
import { cn } from "@/lib/utils";
import { Button, Badge, Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { useLocalStorage } from "@/hooks/useLocalStorage";

export interface BrowserSession {
  id: string;
  url: string;
  title: string;
  screenshot: string; // base64 JPEG data URL
  timestamp: number;
  status: "idle" | "loading" | "running" | "paused";
  actionsPending: number;
}

export function AgentBrowser() {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<BrowserSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [serverStatus, setServerStatus] = useState<string>("disconnected");
  const [pendingAction, setPendingAction] = useState<{
    type: "navigate" | "close" | "approve";
    data: any;
  } | null>(null);
  const [, setBrowserSessionCount] = useLocalStorage("browser-sessions-count", 0);

  // Sync session count to localStorage for Sidebar badge
  useEffect(() => {
    setBrowserSessionCount(sessions.length);
  }, [sessions.length, setBrowserSessionCount]);

  const { messages, isConnected, connect, sendMessage, ws } = useWebSocket(
    WS_AGENT_BROWSER_URL
  );

  // Connect to browser service on mount
  useEffect(() => {
    connect();
    setIsConnecting(true);

    // Listen for session broadcast messages from the backend
    if (ws) {
      ws.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);

        if (data.type === "session_created") {
          setSessions((prev) => {
            if (prev.some((s) => s.id === data.sessionId)) return prev;
            return [
              { id: data.sessionId, ...data.sessionData, timestamp: Date.now() },
              ...prev,
            ];
          });
          setActiveSessionId(data.sessionId);
        } else if (data.type === "session_updated") {
          setSessions((prev) =>
            prev.map((s) =>
              s.id === data.sessionId
                ? { ...s, ...data.sessionData, timestamp: Date.now() }
                : s
            )
          );
        } else if (data.type === "screenshot_frame") {
          setSessions((prev) =>
            prev.map((s) =>
              s.id === activeSessionId
                ? { ...s, screenshot: data.screenshot, status: data.status }
                : s
            )
          );
        } else if (data.type === "server_status") {
          setServerStatus(data.status);
        }
      };

      // Cleanup on unmount
      return () => {
        ws.onmessage = null;
      };
    }
  }, [ws, connect]);

  // Send navigation command to agent
  const navigate = useCallback(
    (url: string) => {
      if (!isConnected || !activeSessionId) return;
      confirmAction("navigate", { url, sessionId: activeSessionId });
    },
    [isConnected, activeSessionId, confirmAction]
  );

  // Send click command to agent (user-approved)
  const click = useCallback(
    (x: number, y: number) => {
      if (!isConnected || !activeSessionId) return;
      sendMessage(JSON.stringify({
        type: "click",
        sessionId: activeSessionId,
        x,
        y,
      }));
    },
    [isConnected, activeSessionId, sendMessage]
  );

  // Send text input to agent
  const type = useCallback(
    (text: string) => {
      if (!isConnected || !activeSessionId) return;
      sendMessage(JSON.stringify({
        type: "type",
        sessionId: activeSessionId,
        text,
      }));
    },
    [isConnected, activeSessionId, sendMessage]
  );

  // Close a session
  const closeSession = useCallback(
    (id: string) => {
      if (!isConnected) return;
      sendMessage(JSON.stringify({
        type: "close_session",
        sessionId: id,
      }));
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) setActiveSessionId(null);
    },
    [isConnected, sendMessage, activeSessionId]
  );

  // Confirm action handler
  const confirmAction = useCallback(
    (type: "navigate" | "close" | "approve", data: any) => {
      setPendingAction({ type, data });
    },
    []
  );

  const executePendingAction = useCallback(() => {
    if (!pendingAction || !isConnected) return;
    const { type, data } = pendingAction;
    
    switch (type) {
      case "navigate":
        navigate(data.url);
        break;
      case "close":
        closeSession(data.id);
        break;
      case "approve":
        sendMessage(JSON.stringify({
          type: "approve",
          sessionId: data.sessionId,
        }));
        break;
    }
    setPendingAction(null);
  }, [pendingAction, isConnected, navigate, closeSession, sendMessage]);

  const cancelPendingAction = useCallback(() => {
    setPendingAction(null);
  }, []);

  // Format timestamp
  const formatTimestamp = useCallback(
    (ts: number) => {
      const date = new Date(ts);
      const now = new Date();
      const diff = now.getTime() - ts;
      if (diff < 60000) return t("just_now");
      if (diff < 3600000) return `${Math.floor(diff / 60000)}${t("minutes_ago")}`;
      if (diff < 86400000) return `${Math.floor(diff / 86400000)}${t("days_ago")}`;
      return `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
    },
    [t]
  );

  if (!isConnected && serverStatus === "connecting") {
    return (
      <div className="flex flex-col h-full items-center justify-center p-8">
        <Badge variant="outline" className="mb-4">
          {t("browser_connecting")}
        </Badge>
        <div className="animate-spin h-12 w-12 border-b-2 border-current" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Browser header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5 flex-nowrap">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary-2 flex items-center justify-center">
            <Send size={16} />
          </div>
          <div>
            <h2 className="font-medium text-sm text-white">{t("browser_agent")}</h2>
            <p className="text-xs text-text-2">
              {t("browser_subtitle")}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Badge
            variant={serverStatus === "healthy" ? "default" : "outline"}
            className="text-xs"
          >
            {serverStatus}
          </Badge>

          {/* New session button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (!isConnected) return;
              sendMessage(JSON.stringify({ type: "new_session" }));
            }}
          >
            {t("new_session")}
          </Button>
        </div>
      </div>

      {/* Sessions list + active view */}
      <div className="flex flex-col flex-1">
        {/* Sessions panel */}
        <div className="w-64 bg-gray-800/50 border-r border-white/5 overflow-y-auto hidden sm:block">
          <div className="p-3">
            <h3 className="text-xs font-medium text-text-2 mb-3">
              {t("active_sessions")}
              {sessions.length > 0 ? `(${sessions.length})` : ""}
            </h3>
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`flex items-center justify-between px-3 py-2 rounded-md cursor-pointer ${
                  activeSessionId === session.id
                    ? "bg-primary/20 text-primary-1"
                    : "text-text-2 hover:bg-primary/10 transition-colors"
                }`}
                onClick={() => setActiveSessionId(session.id)}
              >
                <span className="text-xs">{session.title || session.url.substring(0, 30)}</span>
                <span className="text-[10px] text-text-2/6">
                  {formatTimestamp(session.timestamp)}
                </span>
              </div>
            ))}
            {sessions.length === 0 && (
              <p className="text-[10px] text-text-2/4">{t("no_sessions")}</p>
            )}
          </div>
        </div>

        {/* Browser viewport */}
        <div className="flex-1">
          {/* Active session view */}
          {activeSessionId && sessions.length > 0 ? (
            <BrowserView
              session={sessions.find((s) => s.id === activeSessionId)!}
              onNavigate={navigate}
              onClick={click}
              onType={type}
              onCloseSession={() => closeSession(activeSessionId!)}
            />
          ) : (
            {/* Empty state */}
            <div className="p-8 flex flex-col items-center justify-center h-full text-text-2">
              <h3>{t("no_active_session")}</h3>
              <p>{t("start_new_session")}</p>
              <Button
                onClick={() => sendMessage(JSON.stringify({ type: "new_session" }))}
              >
                {t("create_session")}
              </Button>
            </div>
          )}

          {/* No active session but have sessions */}
          {!activeSessionId && sessions.length > 0 && (
            <div className="p-4 border-t border-white/5">
              <p className="text-sm text-text-2">
                {t("select_session_to_view")}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Control panel (bottom) */}
      <div className="p-4 border-t border-white/5 flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            if (!activeSessionId) return;
            sendMessage(JSON.stringify({
              type: "pause",
              sessionId: activeSessionId,
            }));
          }}
        >
          {t("pause")}
        </Button>

        <Button
          variant="primary"
          size="sm"
          onClick={() => {
            if (!activeSessionId) return;
            confirmAction("approve", { sessionId: activeSessionId });
          }}
        >
          {t("approve_action")}
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            if (!activeSessionId) return;
            sendMessage(JSON.stringify({ type: "new_session" }));
          }}
        >
          {t("new_session")}
        </Button>

        <Button
          variant="danger"
          size="sm"
          onClick={() => {
            if (!activeSessionId) return;
            confirmAction("close", { id: activeSessionId });
          }}
        >
          {t("close_session")}
        </Button>
      </div>
    </div>

    {/* Confirmation Modal */}
    <Modal
      isOpen={!!pendingAction}
      onClose={cancelPendingAction}
      title={
        pendingAction?.type === "navigate"
          ? t("confirm_navigate")
          : pendingAction?.type === "close"
          ? t("confirm_close")
          : t("confirm_approve")
      }
      description={
        pendingAction?.type === "navigate"
          ? t("confirm_navigate_desc", { url: pendingAction.data.url })
          : pendingAction?.type === "close"
          ? t("confirm_close_desc")
          : t("confirm_approve_desc")
      }
      size="sm"
    >
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={cancelPendingAction}>
          {t("cancel")}
        </Button>
        <Button variant="primary" onClick={executePendingAction}>
          {t("confirm")}
        </Button>
      </div>
    </Modal>
    </div>
  );
}

/* ---------- BrowserView sub-component ---------- */

interface BrowserViewProps {
  session: BrowserSession;
  onNavigate: (url: string) => void;
  onClick: (x: number, y: number) => void;
  onType: (text: string) => void;
  onCloseSession: (id: string) => void;
}

function BrowserView({
  session,
  onNavigate,
  onClick,
  onType,
  onCloseSession,
}: BrowserViewProps) {
  return (
    <div>
      {/* Screenshot preview */}
      <div className="h-[calc(100vh_-140px)] bg-black overflow-hidden relative">
        <img
          src={session.screenshot || "/placeholder-browser.svg"}
          alt={session.title || t("browser_viewport")}
          className="w-full h-full object-cover transition-opacity duration-500"
          onError={(e) => {
            e.target.src = "/placeholder-browser.svg";
          }}
        />

        {/* Overlay when no screenshot yet */}
        {!session.screenshot && (
          <div className="absolute inset-0 flex items-center justify-center text-text-2/4">
            <div className="text-center">
              <Send className="w-12 h-12 mb-3" />
              <p>{t("loading_page")}</p>
            </div>
          </div>
        )}

        {/* Action preview overlay */}
        {session.status === "running" && (
          <div className="absolute inset-0 bg-black/30 flex items-center justify-center text-white text-xs">
            <p>{t("agent_thinking")}...</p>
          </div>
        )}
      </div>

      {/* Address bar + controls */}
      <div className="p-3 border-t border-white/5 flex gap-2 flex-wrap">
        <input
          type="text"
          value=""
          onChange={(e) => onNavigate(e.target.value)}
          placeholder={t("enter_url")}
          className="flex-1 bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
        />
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onNavigate("about:blank")}
          className="hidden sm:block"
        >
          {t("new_tab")}
        </Button>
      </div>
    </div>
  );
}