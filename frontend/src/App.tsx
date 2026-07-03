import { BrowserRouter, Route, Routes } from "react-router";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { GlobalHotkeys } from "@/components/layout/GlobalHotkeys";
import QueryProvider from "@/providers/QueryProvider";
import CommandCenterPage from "@/pages/CommandCenter";
import MatchesPage from "@/pages/Matches";
import MatchDetailPage from "@/pages/MatchDetail";
import TournamentPage from "@/pages/Tournament";
import OpportunitiesPage from "@/pages/Opportunities";
import ConsolePage from "@/pages/Console";
import ModelsPage from "@/pages/Models";
import PerformancePage from "@/pages/Performance";
import LedgerPage from "@/pages/Ledger";
import OpsPage from "@/pages/Ops";
import MatchdayPage from "@/pages/Matchday";

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
            </main>
          </div>
        </div>
      </QueryProvider>
    </BrowserRouter>
  );
}
