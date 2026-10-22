import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { claim, claimRoutes, claimRow, json, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

function routes() {
  stubApi({
    "GET /api/claims": () => json([claimRow()]),
    "GET /api/instructions": () => json({ text: "Version 2026.1" }),
  });
}

it("opens on the queue", async () => {
  routes();
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
  expect(
    screen.getByRole("link", { name: "Queue" }).getAttribute("aria-current"),
  ).toBe("page");
});

it("follows the hash to the instructions and back", async () => {
  routes();
  render(<App />);
  await screen.findByRole("heading", { name: "Claims queue" });
  act(() => {
    window.location.hash = "#/instructions";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(
    await screen.findByRole("heading", { name: "Agent instructions" }),
  ).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Instructions" })
      .getAttribute("aria-current"),
  ).toBe("page");
});

it("opens a claim from its hash", async () => {
  stubApi(claimRoutes(() => claim()));
  window.location.hash = "#/claims/CLM-1001";
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "CLM-1001" }),
  ).toBeDefined();
  expect(screen.getByRole("link", { name: "Back to the queue" })).toBeDefined();
});
