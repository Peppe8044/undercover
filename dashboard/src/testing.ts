import { vi } from "vitest";
import type { ClaimRow } from "./api";

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function stubApi(routes: Partial<Record<string, () => Response>>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const route = routes[`${init?.method ?? "GET"} ${path}`];
    return Promise.resolve(
      route ? route() : json({ detail: `No route for ${path}` }, 404),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function claimRow(overrides: Partial<ClaimRow> = {}): ClaimRow {
  return {
    claim_id: "CLM-1001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    summary: "Flight home canceled by the airline",
    amount_claimed: 420,
    submitted_on: "2026-06-24",
    status: "waiting",
    decision: null,
    payout: null,
    ...overrides,
  };
}
