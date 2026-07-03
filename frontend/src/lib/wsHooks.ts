import { useEffect, useRef, useSyncExternalStore } from "react";
import { terminalSocket, type WsMessage, type WsStatus } from "./ws";

/** Subscribe to a topic for the lifetime of the component. The handler ref is
 * kept current so callers can pass inline closures without resubscribing. */
export function useTopic<T = unknown>(topic: string, handler: (msg: WsMessage<T>) => void): void {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(
    () => terminalSocket.subscribe(topic, (msg) => ref.current(msg as WsMessage<T>)),
    [topic],
  );
}

export function useWsStatus(): WsStatus {
  return useSyncExternalStore(
    terminalSocket.onStatusChange,
    terminalSocket.getStatus,
    () => "down",
  );
}
