import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { GlobalHotkeys } from "@/components/layout/GlobalHotkeys";
import QueryProvider from "@/providers/QueryProvider";
import CommandCenterPage from "@/pages/CommandCenter";
import MatchesPage from "@/pages/Matches";
import TournamentPage from "@/pages/Tournament";
import OpportunitiesPage from "@/pages/Opportunities";
import ConsolePage from "@/pages/Console";
import LedgerPage from "@/pages/Ledger";
import OpsPage from "@/pages/Ops";
import MatchdayPage from "@/pages/Matchday";

// Chart-heavy routes (recharts consumers) are lazy so the library stays out
// of the main chunk - this is what keeps the gzip budget in frontend README
// honest. Everything the operator needs in the first second (board, console,
// ledger, matchday) is eager.
const MatchDetailPage = lazy(() => import("@/pages/MatchDetail"));
const ModelsPage = lazy(() => import("@/pages/Models"));
const PerformancePage = lazy(() => import("@/pages/Performance"));

const lazyFallback = (
  <div className="p-8 text-center text-muted-foreground animate-pulse">Loading…</div>
);

/** Terminal shell: rail + status strip + routed content (ADR-0013).
 * Route table mirrors NAV_ITEMS in Sidebar; both change together. */
export function App() {
  return (
    <BrowserRouter>
      <QueryProvider>
        <div className="flex h-screen">
          <GlobalHotkeys />
          <CommandPalette />
          <Sidebar />
          <div className="flex flex-col flex-1 overflow-hidden">
            <Topbar />
            <main className="flex-1 overflow-auto p-4 md:p-6 lg:p-8">
              <Suspense fallback={lazyFallback}>
                <Routes>
                  <Route path="/" element={<CommandCenterPage />} />
                  <Route path="/matches" element={<MatchesPage />} />
                  <Route path="/matches/:matchId" element={<MatchDetailPage />} />
                  <Route path="/tournament" element={<TournamentPage />} />
                  <Route path="/opportunities" element={<OpportunitiesPage />} />
                  <Route path="/console" element={<ConsolePage />} />
                  <Route path="/models" element={<ModelsPage />} />
                  <Route path="/performance" element={<PerformancePage />} />
                  <Route path="/ledger" element={<LedgerPage />} />
                  <Route path="/ops" element={<OpsPage />} />
                  <Route path="/matchday" element={<MatchdayPage />} />
                </Routes>
              </Suspense>
            </main>
          </div>
        </div>
      </QueryProvider>
    </BrowserRouter>
  );
}
