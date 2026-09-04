/**
 * Browser Agent WebSocket message types
 * Matching the backend: apps/backend/app/services/browser_service.py
 * and frontend: apps/frontend/src/components/Browser/AgentBrowser.tsx
 */

export type BrowserMessageType =
  | "new_session"
  | "navigate"
  | "click"
  | "type"
  | "close_session"
  | "pause"
  | "approve"
  | "request_screenshot"
  | "error";

export interface BaseBrowserMessage {
  type: BrowserMessageType;
  sessionId?: string;
}

export interface NewSessionMsg extends BaseBrowserMessage {
  type: "new_session";
}

export interface NavigateMsg extends BaseBrowserMessage {
  type: "navigate";
  url: string;
}

export interface ClickMsg extends BaseBrowserMessage {
  type: "click";
  x: number;
  y: number;
}

export interface TypeMsg extends BaseBrowserMessage {
  type: "type";
  text: string;
}

export interface CloseSessionMsg extends BaseBrowserMessage {
  type: "close_session";
}

export interface PauseMsg extends BaseBrowserMessage {
  type: "pause";
}

export interface ApproveMsg extends BaseBrowserMessage {
  type: "approve";
}

export interface ScreenshotFrameMsg extends BaseBrowserMessage {
  type: "request_screenshot";
  screenshot: string; // base64 JPEG data URL
  status: "idle" | "loading" | "running" | "paused";
}

export interface ErrorMsg extends BaseBrowserMessage {
  type: "error";
  content: string;
}

// Union of all possible messages from backend to frontend
export type BrowserBackendMessage =
  | NewSessionMsg
  | NavigateMsg
  | ClickMsg
  | TypeMsg
  | CloseSessionMsg
  | PauseMsg
  | ApproveMsg
  | ScreenshotFrameMsg
  | ErrorMsg;

// Message from frontend to backend
export interface BrowserFrontendMessage {
  type: BrowserMessageType;
  sessionId: string;
  payload?: {
    url?: string;
    x?: number;
    y?: number;
    text?: string;
  };
}

// Response from backend to frontend (session state)
export interface BrowserSessionState {
  id: string;
  url: string;
  title: string;
  screenshot: string; // base64 JPEG data URL
  status: "idle" | "loading" | "running" | "paused";
  actionsPending: number;
}