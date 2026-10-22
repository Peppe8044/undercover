import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Instructions } from "./Instructions";
import { json, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the agent's instructions, read only", async () => {
  stubApi({
    "GET /api/instructions": () =>
      json({ text: "# The UnderCover Agent\n\nVersion 2026.1" }),
  });
  render(<Instructions />);
  expect(
    (await screen.findByText(/Version 2026.1/)).textContent.startsWith(
      "# The UnderCover Agent",
    ),
  ).toBe(true);
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("says when the backend can't be reached", async () => {
  stubApi({});
  render(<Instructions />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "No route for /api/instructions",
  );
});

it("shows a status code when the backend gives no detail", async () => {
  stubApi({ "GET /api/instructions": () => new Response("", { status: 502 }) });
  render(<Instructions />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "The backend answered 502.",
  );
});
