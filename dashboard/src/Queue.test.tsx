import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Queue } from "./Queue";
import { claimRow, json, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const claims = [
  claimRow(),
  claimRow({
    claim_id: "CLM-1002",
    customer_name: "Tom Okafor",
    claim_type: "baggage",
    amount_claimed: 1150,
    status: "waiting_for_sign_off",
    decision: "approve",
    payout: 1150,
  }),
  claimRow({
    claim_id: "CLM-1003",
    status: "decided",
    decision: "decline",
    payout: 0,
  }),
];

it("shows every claim with its state, decision and payout", async () => {
  stubApi({ "GET /api/claims": () => json(claims) });
  render(<Queue />);
  const link = await screen.findByRole("link", { name: "CLM-1002" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1002");
  const row = link.closest("tr");
  expect(row).not.toBeNull();
  if (!row) return;
  const cells = within(row);
  expect(cells.getByText("Tom Okafor")).toBeDefined();
  expect(cells.getByText("Baggage")).toBeDefined();
  expect(cells.getByText("Waiting for sign-off")).toBeDefined();
  expect(cells.getByText("Approve")).toBeDefined();
  expect(cells.getAllByText("$1,150.00")).toHaveLength(2);
  expect(screen.getAllByText("$420.00")).toHaveLength(2);
  expect(screen.getByText("Decline")).toBeDefined();
});

it("counts the claims in each state", async () => {
  stubApi({ "GET /api/claims": () => json(claims) });
  render(<Queue />);
  expect((await screen.findByTestId("count-waiting")).textContent).toBe("1");
  expect(screen.getByTestId("count-in_progress").textContent).toBe("0");
  expect(screen.getByTestId("count-waiting_for_sign_off").textContent).toBe(
    "1",
  );
  expect(screen.getByTestId("count-decided").textContent).toBe("1");
});

it("refreshes every two seconds", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const fetchMock = stubApi({ "GET /api/claims": () => json(claims) });
  render(<Queue />);
  await screen.findByRole("link", { name: "CLM-1001" });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(2000);
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("says when the backend can't be reached", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toContain("offline");
});

it("shows the backend's error", async () => {
  stubApi({
    "GET /api/claims": () => json({ detail: "Database is locked." }, 500),
  });
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Database is locked.",
  );
});
