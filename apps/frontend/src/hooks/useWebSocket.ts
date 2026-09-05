import { useState, useCallback, useRef } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "status" | "error";
  content: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
  thinking?: string;
  isStreaming?: boolean;
}

export function useWebSocket(url: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => {
      setIsConnected(false);
      setIsThinking(false);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "status" && data.content === "thinking") {
        setIsThinking(true);
      }

      if (data.type === "message") {
        setIsThinking(false);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: data.content,
            timestamp: new Date(),
            metadata: data.metadata,
          },
        ]);
      }

      if (data.type === "error") {
        setIsThinking(false);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "error",
            content: data.content,
            timestamp: new Date(),
          },
        ]);
      }
    };
  }, [url]);

  const sendMessage = useCallback(
    (content: string, extra?: { provider_id?: string | null; model?: string | null }) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          message: content,
          provider_id: extra?.provider_id ?? null,
          model: extra?.model ?? null,
        }));
      }
    },
    [],
  );

  const disconnect = useCallback(() => {
    wsRef.current?.close();
  }, []);

  return { messages, isConnected, isThinking, connect, sendMessage, disconnect };
}
