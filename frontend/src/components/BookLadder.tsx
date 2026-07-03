/**
 * BookLadder (ADR-0016: bespoke, custom DOM): venue depth with MY resting
 * quotes overlaid at their price levels.
 *
 * Honesty rules this component owns:
 *  - depth bars scale to the max size ON SCREEN (declared in the corner), so
 *    a thin book cannot cosplay as a deep one;
 *  - my quotes render as overlay rows in series-1 - never in a status or
 *    direction hue (a resting quote is not an edge claim);
 *  - when quotes are pulled (paused/killed), the overlay rows say PULLED
 *    instead of silently vanishing - absence must be legible;
 *  - `stale` dims the whole ladder and stamps it: an old book must not look
 *    tradeable.
 */
import type { ConsoleState } from "@/lib/api";

const px = (p: number) => p.toFixed(3);

function DepthRow({
  price,
  size,
  maxSize,
  side,
}: {
  price: number;
  size: number;
  maxSize: number;
  side: "bid" | "ask";
}) {
  return (
    <div className="relative flex h-6 items-center font-mono text-xs">
      <div
        className={`absolute inset-y-0.5 ${side === "bid" ? "left-1/2" : "right-1/2"} bg-muted/50`}
        style={{ width: `${(48 * size) / maxSize}%` }}
      />
      <span className="z-10 w-1/2 pr-2 text-right">{side === "ask" ? px(price) : ""}</span>
      <span className="z-10 w-1/2 pl-2">{side === "bid" ? px(price) : ""}</span>
      <span className="absolute right-1 z-10 text-[10px] text-muted-foreground">{size}</span>
    </div>
  );
}

function MyQuoteRow({ price, size, active, label }: { price: number; size: number; active: boolean; label: string }) {
  return (
    <div
      className={`flex h-6 items-center justify-between rounded border px-2 font-mono text-xs ${
        active ? "border-series-1/60 bg-series-1/10" : "border-border bg-muted/30 text-muted-foreground"
      }`}
      data-testid={`my-${label.toLowerCase().replace(" ", "-")}`}
    >
      <span className="font-semibold">{label}</span>
      <span>
        {active ? `${px(price)} × ${size}` : "PULLED"}
      </span>
    </div>
  );
}

export function BookLadder({ console: c, stale }: { console: ConsoleState; stale: boolean }) {
  const maxSize = Math.max(...c.book_bids.map((l) => l.size), ...c.book_asks.map((l) => l.size), 1);
  const spread = c.book_asks[0].price - c.book_bids[0].price;
  return (
    <div className={`space-y-0.5 ${stale ? "opacity-45" : ""}`} data-testid="book-ladder" data-stale={stale}>
      {stale && (
        <div className="rounded border border-status-warn/60 bg-status-warn/10 px-2 py-1 text-xs font-bold text-status-warn">
          BOOK STALE — feed down; do not read these levels as live.
        </div>
      )}
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>asks ↑</span>
        <span>bars scaled to max {maxSize} on screen</span>
      </div>
      {[...c.book_asks].reverse().map((l) => (
        <DepthRow key={`a${l.price}`} price={l.price} size={l.size} maxSize={maxSize} side="ask" />
      ))}
      <MyQuoteRow price={c.my_quotes.ask} size={c.my_quotes.size} active={c.my_quotes.active} label="MY ASK" />
      <div className="flex items-center justify-center gap-2 py-0.5 text-[10px] text-muted-foreground">
        — venue spread {px(spread)} —
      </div>
      <MyQuoteRow price={c.my_quotes.bid} size={c.my_quotes.size} active={c.my_quotes.active} label="MY BID" />
      {c.book_bids.map((l) => (
        <DepthRow key={`b${l.price}`} price={l.price} size={l.size} maxSize={maxSize} side="bid" />
      ))}
      <div className="text-[10px] text-muted-foreground">bids ↓</div>
    </div>
  );
}
