/**
 * Multiplexed WebSocket client (ADR-0014): ONE socket, topic handlers, ONE
 * reconnect path with exponential backoff + jitter and automatic resubscribe.
 *
 * Server state received here flows into the TanStack Query cache (the handler
 * decides), so components read one source of truth whether a value arrived by
 * REST or by push. The socket's connection status is surfaced to the status
 * strip: when this is "down", the terminal must look degraded, not merely quiet.
 */

export interface WsMessage<T = unknown> {
  topic: string;
  source: "real" | "mock";
  ts_utc: string;
  data: T;
}

export type WsStatus = "connecting" | "open" | "down";

type Handler = (msg: WsMessage) => void;

const WS_URL =
  (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(/^http/, "ws") +
  "/api/v1/ws";

class TerminalSocket {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<Handler>>();
  private status: WsStatus = "down";
  private statusListeners = new Set<() => void>();
  private backoffMs = 1_000;
  private started = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  private setStatus(s: WsStatus) {
    if (this.status === s) return;
    this.status = s;
    for (const l of this.statusListeners) l();
  }

  getStatus = (): WsStatus => this.status;

  onStatusChange = (listener: () => void): (() => void) => {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  };

  private start() {
    if (this.started || typeof window === "undefined") return;
    this.started = true;
    this.connect();
  }

  private connect() {
    // Guard the single-reconnect-path invariant: any pending retry is
    // superseded by this attempt, so two connect paths can never race.
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.setStatus("connecting");
    const ws = new WebSocket(WS_URL);
    this.ws = ws;

    ws.onopen = () => {
      this.backoffMs = 1_000;
      this.setStatus("open");
      const topics = [...this.handlers.keys()];
      if (topics.length > 0) ws.send(JSON.stringify({ subscribe: topics }));
    };

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data) as WsMessage;
      for (const h of this.handlers.get(msg.topic) ?? []) h(msg);
    };

    ws.onclose = () => {
      this.setStatus("down");
      this.ws = null;
      const jitter = Math.random() * 0.3 * this.backoffMs;
      this.reconnectTimer = setTimeout(() => this.connect(), this.backoffMs + jitter);
      this.backoffMs = Math.min(this.backoffMs * 2, 30_000);
    };

    ws.onerror = () => ws.close();
  }

  subscribe(topic: string, handler: Handler): () => void {
    this.start();
    let set = this.handlers.get(topic);
    const isNewTopic = !set;
    if (!set) {
      set = new Set();
      this.handlers.set(topic, set);
    }
    set.add(handler);
    if (isNewTopic && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ subscribe: [topic] }));
    }
    return () => {
      set.delete(handler);
      if (set.size === 0) {
        this.handlers.delete(topic);
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ unsubscribe: [topic] }));
        }
      }
    };
  }
}

export const terminalSocket = new TerminalSocket();
