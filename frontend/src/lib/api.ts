/**
 * Typed API client (ADR-0011, ADR-0012).
 *
 * Types are generated from the backend's OpenAPI schema (`npm run gen:api`
 * after `make openapi`), so a backend schema change that the UI doesn't
 * handle becomes a compile error here, not a runtime surprise on matchday.
 *
 * Every fetcher returns the full Envelope {data, provenance} - never the bare
 * data. Components must consume provenance (source, data_as_of) to render;
 * stripping it at the fetch layer is how mock or stale numbers end up looking
 * real on screen.
 */
import createClient from "openapi-fetch";
import type { components, paths } from "./api.types";

export type Provenance = components["schemas"]["Provenance"];
export type HealthData = components["schemas"]["HealthData"];
export type MatchPrediction = components["schemas"]["MatchPrediction"];
export type MarketOpportunity = components["schemas"]["MarketOpportunity"];
export type LedgerPage = components["schemas"]["LedgerPage"];
export type RunOut = components["schemas"]["RunOut"];

export interface Envelope<T> {
  data: T;
  provenance: Provenance;
}

const client = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
});

function unwrap<T>(res: { data?: T; error?: unknown }, what: string): T {
  if (res.error !== undefined || res.data === undefined) {
    throw new Error(`${what} failed: ${JSON.stringify(res.error)}`);
  }
  return res.data;
}

export async function fetchHealth(): Promise<Envelope<HealthData>> {
  return unwrap(await client.GET("/api/v1/health"), "GET /api/v1/health");
}

export async function fetchMatches(): Promise<Envelope<MatchPrediction[]>> {
  return unwrap(await client.GET("/api/v1/matches"), "GET /api/v1/matches");
}

export async function fetchOpportunities(): Promise<Envelope<MarketOpportunity[]>> {
  return unwrap(await client.GET("/api/v1/opportunities"), "GET /api/v1/opportunities");
}

export async function fetchLedger(params?: {
  after_seq?: number;
  kind?: string;
  limit?: number;
}): Promise<Envelope<LedgerPage>> {
  return unwrap(
    await client.GET("/api/v1/ledger", { params: { query: params } }),
    "GET /api/v1/ledger",
  );
}

export type LedgerVerification = components["schemas"]["LedgerVerification"];
export type RunsPage = components["schemas"]["RunsPage"];

export async function fetchLedgerVerify(): Promise<Envelope<LedgerVerification>> {
  return unwrap(await client.GET("/api/v1/ledger/verify"), "GET /api/v1/ledger/verify");
}

export async function fetchRuns(): Promise<Envelope<RunsPage>> {
  return unwrap(await client.GET("/api/v1/runs"), "GET /api/v1/runs");
}
