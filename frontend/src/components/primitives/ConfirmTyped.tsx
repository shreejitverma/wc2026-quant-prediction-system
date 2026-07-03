"use client";

/**
 * ConfirmTyped: the gate in front of anything live-affecting. The confirm
 * button stays disabled until the exact phrase is typed; if the action itself
 * is not yet wired (no backend command endpoint), `disabledReason` states why
 * and the button can never enable - the dialog teaches the muscle memory
 * without pretending a fence exists where it does not.
 */

import { useEffect, useRef, useState } from "react";

export interface ConfirmTypedProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  phrase: string;
  confirmLabel: string;
  onConfirm?: () => void;
  disabledReason?: string;
}

export function ConfirmTyped({
  open,
  onOpenChange,
  title,
  description,
  phrase,
  confirmLabel,
  onConfirm,
  disabledReason,
}: ConfirmTypedProps) {
  const [typed, setTyped] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTyped("");
      inputRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  if (!open) return null;

  const armed = typed === phrase && !disabledReason && onConfirm !== undefined;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={() => onOpenChange(false)}
    >
      <div
        className="w-full max-w-md rounded-lg border border-status-critical/50 bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-status-critical">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
        {disabledReason && (
          <p className="mt-3 rounded border border-status-warn/50 bg-status-warn/10 px-3 py-2 text-xs text-status-warn">
            {disabledReason}
          </p>
        )}
        <label className="mt-4 block text-xs text-muted-foreground">
          Type <span className="font-mono font-bold text-foreground">{phrase}</span> to confirm
        </label>
        <input
          ref={inputRef}
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          autoComplete="off"
          spellCheck={false}
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </button>
          <button
            disabled={!armed}
            onClick={() => {
              if (armed) {
                onConfirm?.();
                onOpenChange(false);
              }
            }}
            className="rounded-md bg-status-critical px-3 py-1.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
