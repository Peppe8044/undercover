import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Step } from "./api";
import { ClaimPage } from "./ClaimPage";
import { claim, claimRoutes, json, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows a waiting claim in full", async () => {
  stubApi(claimRoutes(() => claim()));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Waiting")).toBeDefined();
  expect(
    screen.getByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Airport hotel")).toBeDefined();
  expect(screen.getByText("$245.00")).toBeDefined();
  expect(screen.getByText("Hotel receipt")).toBeDefined();
  expect(
    screen.getByText("The agent hasn't started this claim."),
  ).toBeDefined();
  expect(screen.getByText("No steps yet.")).toBeDefined();
  expect(await screen.findByText("UnderCover Premium")).toBeDefined();
  expect(screen.getByText("None")).toBeDefined();
  expect(await screen.findByText("CLM-0412")).toBeDefined();
  expect(screen.getByText("Maya Patel's earlier claims")).toBeDefined();
});

it("shows a decided claim with its reason and payment", async () => {
  stubApi(
    claimRoutes(() =>
      claim({
        status: "decided",
        decision: "approve",
        payout: 420,
        reason: "The delay was over six hours.",
        policy_section: "Section 3, Trip Delay",
        paid_amount: 420,
        paid_at: "2026-10-22T02:52:02+00:00",
      }),
    ),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByText("The delay was over six hours."),
  ).toBeDefined();
  expect(screen.getByText("Approve")).toBeDefined();
  expect(screen.getByText("Section 3, Trip Delay")).toBeDefined();
  expect(screen.getByText("Paid $420.00")).toBeDefined();
  expect(screen.queryByRole("button", { name: "Sign off and pay" })).toBeNull();
});

it("shows a decline and a claim in progress", async () => {
  stubApi(
    claimRoutes(() =>
      claim({
        status: "decided",
        decision: "decline",
        payout: 0,
        reason: "Not covered.",
        policy_section: "Section 9",
      }),
    ),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("No payment")).toBeDefined();
  cleanup();
  stubApi(claimRoutes(() => claim({ status: "in_progress" })));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findAllByText("The agent is working on this claim."),
  ).toHaveLength(2);
});

it("lists the agent's steps", async () => {
  const steps: Step[] = [
    {
      step_id: 1,
      kind: "tool_call",
      content: 'get_claim {"claim_id": "CLM-1001"}',
      created_at: "2026-10-22T02:52:02+00:00",
    },
    {
      step_id: 2,
      kind: "tool_result",
      content: `get_claim: ${"x".repeat(200)}`,
      created_at: "2026-10-22T02:52:03+00:00",
    },
    {
      step_id: 3,
      kind: "model",
      content: "Approve, $420.00.",
      created_at: "2026-10-22T02:52:04+00:00",
    },
  ];
  stubApi(claimRoutes(() => claim({ status: "in_progress" }), steps));
  render(<ClaimPage claimId="CLM-1001" />);
  const call = await screen.findByText('get_claim {"claim_id": "CLM-1001"}');
  const items = within(call.closest("ol") ?? document.body).getAllByRole(
    "listitem",
  );
  expect(
    items.map((item) => item.querySelector(".step-kind")?.textContent),
  ).toEqual(["Tool call", "Result", "Agent"]);
  expect(screen.getByText(/^get_claim: x+\.\.\.$/)).toBeDefined();
  expect(screen.getByText("Approve, $420.00.")).toBeDefined();
});

it("signs off a payout over the limit, which pays it", async () => {
  let current = claim({
    claim_id: "CLM-1002",
    status: "waiting_for_sign_off",
    decision: "approve",
    payout: 1150,
    reason: "The suitcase was lost.",
    policy_section: "Section 5",
  });
  const fetchMock = stubApi({
    ...claimRoutes(() => current),
    "POST /api/claims/CLM-1002/sign-off": () => {
      current = {
        ...current,
        status: "decided",
        paid_amount: 1150,
        signed_off_by: { handler_id: "HND-03", name: "Priya Raman" },
      };
      return json(current);
    },
  });
  render(<ClaimPage claimId="CLM-1002" />);
  expect(
    await screen.findByText("Waiting for sign-off", { selector: "dd" }),
  ).toBeDefined();
  const button = screen.getByRole("button", { name: "Sign off and pay" });
  expect(button.hasAttribute("disabled")).toBe(true);
  await screen.findByRole("option", { name: "Priya Raman" });
  fireEvent.change(screen.getByRole("combobox", { name: "Handler" }), {
    target: { value: "HND-03" },
  });
  fireEvent.click(button);
  expect(
    await screen.findByText("Paid $1,150.00, signed off by Priya Raman"),
  ).toBeDefined();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1002/sign-off",
    expect.objectContaining({ body: JSON.stringify({ handler_id: "HND-03" }) }),
  );
});

it("shows why a sign-off was refused", async () => {
  const held = claim({
    claim_id: "CLM-1002",
    status: "waiting_for_sign_off",
    decision: "approve",
    payout: 1150,
    reason: "The suitcase was lost.",
    policy_section: "Section 5",
  });
  stubApi({
    ...claimRoutes(() => held),
    "POST /api/claims/CLM-1002/sign-off": () =>
      json({ detail: "CLM-1002 is not waiting for sign-off." }, 409),
  });
  render(<ClaimPage claimId="CLM-1002" />);
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(screen.getByRole("combobox", { name: "Handler" }), {
    target: { value: "HND-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "CLM-1002 is not waiting for sign-off.",
  );
});

it("says when a claim can't be found", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-0000" />);
  expect((await screen.findByRole("alert")).textContent).toContain("No route");
});
