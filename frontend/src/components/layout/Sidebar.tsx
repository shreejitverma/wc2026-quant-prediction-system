import { Link, useLocation } from "react-router";
import {
  Activity,
  BookLock,
  Gauge,
  LayoutDashboard,
  Radar,
  Swords,
  TrendingUp,
  Trophy,
  Wrench,
} from "lucide-react";

/** One rail entry per decision the screen supports (see PlannedScreen stubs
 * for the ones not yet built). Order mirrors the operator's day: state of the
 * world, then opportunities, then execution, then judgment, then plumbing. */
export const NAV_ITEMS = [
  { name: "Command Center", href: "/", icon: LayoutDashboard },
  { name: "Matches", href: "/matches", icon: Swords },
  { name: "Tournament", href: "/tournament", icon: Trophy },
  { name: "Opportunities", href: "/opportunities", icon: TrendingUp },
  { name: "MM Console", href: "/console", icon: Activity },
  { name: "Model Race", href: "/models", icon: Radar },
  { name: "Performance", href: "/performance", icon: Gauge },
  { name: "Ledger", href: "/ledger", icon: BookLock },
  { name: "Ops", href: "/ops", icon: Wrench },
] as const;

export function Sidebar() {
  const { pathname } = useLocation();
  return (
    <div className="flex h-full w-56 flex-col border-r bg-background">
      <div className="flex h-14 items-center border-b px-4">
        <h1 className="text-sm font-bold tracking-tight">WC2026 TERMINAL</h1>
      </div>
      <div className="flex-1 overflow-auto py-2">
        <nav className="grid gap-1 px-2">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                to={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground ${
                  active ? "bg-accent text-accent-foreground" : "text-muted-foreground"
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="border-t px-4 py-2 text-[10px] text-muted-foreground">
        ⌘K palette · ⇧⌘K kill switch
      </div>
    </div>
  );
}
