"use client";

/**
 * OddsTicker: a price that shows its own last move. Tick direction uses
 * neutral ink glyphs, NOT the edge hues - "price went up" is not "good for
 * me", and reusing the polarity colors here would teach the eye a lie.
 */

import { useEffect, useRef, useState } from "react";

export function OddsTicker({ price, decimals = 2 }: { price: number; decimals?: number }) {
  const prev = useRef<number | null>(null);
  const [dir, setDir] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (prev.current !== null && price !== prev.current) {
      setDir(price > prev.current ? "up" : "down");
      const id = setTimeout(() => setDir(null), 900);
      prev.current = price;
      return () => clearTimeout(id);
    }
    prev.current = price;
  }, [price]);

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono transition-colors ${
        dir ? "text-foreground" : "text-foreground/90"
      }`}
      data-tick={dir ?? "flat"}
    >
      {price.toFixed(decimals)}
      <span className="w-3 text-xs text-muted-foreground">
        {dir === "up" ? "↑" : dir === "down" ? "↓" : ""}
      </span>
    </span>
  );
}
