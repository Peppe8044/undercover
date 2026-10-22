import { expect, test, type APIRequestContext } from "@playwright/test";

// The tests stand in for the agent through the API, so they never call a model.
async function decide(
  request: APIRequestContext,
  claimId: string,
  payout: number,
) {
  await request.post(`/api/claims/${claimId}/start`, {
    data: { thread_id: "e2e" },
  });
  const response = await request.post(`/api/claims/${claimId}/decision`, {
    data: {
      decision: "approve",
      payout,
      reason: "The wording covers the loss.",
      policy_section: "Section 3, Trip Delay",
    },
  });
  expect(response.ok()).toBe(true);
}

test("the queue shows every claim waiting", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(25);
  await expect(page.getByTestId("count-waiting")).toHaveText("25");
});

test("a claim page shows the claim in full", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page.getByText(/^My flight home from Rome/)).toBeVisible();
  await expect(page.locator("article.document")).toHaveCount(4);
  await expect(page.getByText("Airport hotel, one night")).toBeVisible();
  await expect(page.getByText("UnderCover Premium")).toBeVisible();
  await expect(page.getByText("CLM-0412")).toBeVisible();
});

test("the agent's steps show as it works, and it pays an approval", async ({
  page,
  request,
}) => {
  await page.goto("/#/claims/CLM-1001");
  await expect(page.getByText("No steps yet.")).toBeVisible();
  await request.post("/api/claims/CLM-1001/start", {
    data: { thread_id: "e2e" },
  });
  await request.post("/api/claims/CLM-1001/steps", {
    data: { kind: "tool_call", content: 'get_claim {"claim_id": "CLM-1001"}' },
  });
  await expect(
    page.getByText('get_claim {"claim_id": "CLM-1001"}'),
  ).toBeVisible();
  await expect(page.locator(".claim-head")).toContainText("In progress");
  await request.post("/api/claims/CLM-1001/decision", {
    data: {
      decision: "approve",
      payout: 420,
      reason: "The delay was over the waiting period.",
      policy_section: "Section 3, Trip Delay",
    },
  });
  const paid = await request.post("/api/claims/CLM-1001/payment", {
    data: { amount: 420 },
  });
  expect(paid.ok()).toBe(true);
  await expect(page.getByText("Paid $420.00")).toBeVisible();
  await expect(page.locator(".claim-head")).toContainText("Decided");
  await expect(
    page.getByText("The delay was over the waiting period."),
  ).toBeVisible();
});

test("a payout over $1,000 waits for a handler's sign-off", async ({
  page,
  request,
}) => {
  await decide(request, "CLM-1002", 1150);
  const refused = await request.post("/api/claims/CLM-1002/payment", {
    data: { amount: 1150 },
  });
  expect(refused.status()).toBe(403);

  await page.goto("/#/claims/CLM-1002");
  await expect(page.locator(".claim-head")).toContainText(
    "Waiting for sign-off",
  );
  await page
    .getByRole("combobox", { name: "Handler" })
    .selectOption({ label: "Priya Raman" });
  await page.getByRole("button", { name: "Sign off and pay" }).click();
  await expect(
    page.getByText("Paid $1,150.00, signed off by Priya Raman"),
  ).toBeVisible();
  await expect(page.locator(".claim-head")).toContainText("Decided");

  await page.getByRole("link", { name: "Back to the queue" }).click();
  await expect(page.getByTestId("count-decided")).toHaveText("2");
});

test("the agent's instructions are read only", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(page.locator("pre.instructions")).toContainText(
    "Version 2026.1",
  );
  await expect(page.getByRole("textbox")).toHaveCount(0);
});
