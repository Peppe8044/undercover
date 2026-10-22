import { vi } from "vitest";
import type { Claim, ClaimRow, Customer, Handler, Policy, Step } from "./api";

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

export function claim(overrides: Partial<Claim> = {}): Claim {
  return {
    claim_id: "CLM-1001",
    policy_id: "POL-2001",
    customer_id: "CUS-3001",
    claim_type: "trip_delay",
    submitted_on: "2026-06-24",
    incident_date: "2026-06-18",
    incident_location: "Rome, Italy",
    summary: "Flight home canceled by the airline",
    story: "My flight home from Rome was canceled.",
    items: [
      { description: "Airport hotel", category: "accommodation", amount: 245 },
      { description: "Dinner and breakfast", category: "meals", amount: 95 },
      { description: "Taxis", category: "transport", amount: 80 },
    ],
    amount_claimed: 420,
    documents: [
      {
        name: "Hotel receipt",
        type: "receipt",
        content: "Hotel Aurelia Fiumicino. Total paid: $245.00.",
      },
    ],
    status: "waiting",
    thread_id: null,
    decision: null,
    payout: null,
    reason: null,
    policy_section: null,
    decided_at: null,
    paid_amount: null,
    paid_at: null,
    signed_off_by: null,
    signed_off_at: null,
    ...overrides,
  };
}

export const policy: Policy = {
  policy_id: "POL-2001",
  plan: "premium",
  add_ons: [],
  purchased_on: "2026-04-22",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
  plan_details: { name: "UnderCover Premium", deductible: 50 },
  add_on_details: [],
};

export const customer: Customer = {
  customer_id: "CUS-3001",
  name: "Maya Patel",
  customer_since: "2023-04-11",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      filed_on: "2024-08-19",
      claim_type: "baggage_delay",
      summary: "Checked bag arrived 30 hours late in Lisbon",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

export const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
    can_approve_over_limit: true,
  },
  {
    handler_id: "HND-03",
    name: "Priya Raman",
    role: "Claims Handler",
    can_approve_over_limit: true,
  },
];

export function claimRoutes(
  current: () => Claim,
  steps: Step[] = [],
): Partial<Record<string, () => Response>> {
  const id = current().claim_id;
  return {
    [`GET /api/claims/${id}`]: () => json(current()),
    [`GET /api/claims/${id}/steps`]: () => json(steps),
    [`GET /api/policies/${current().policy_id}`]: () => json(policy),
    [`GET /api/customers/${current().customer_id}`]: () => json(customer),
    "GET /api/handlers": () => json(handlers),
  };
}
