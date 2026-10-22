import { expect, it } from "vitest";
import { label, money, time } from "./format";

it("formats money in US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
});

it("turns codes into labels", () => {
  expect(label("trip_delay")).toBe("Trip delay");
  expect(label("baggage")).toBe("Baggage");
});

it("shows the time of day", () => {
  expect(time("2026-10-22T02:52:02+00:00")).toMatch(/\d{1,2}:52:02\s[AP]M/);
});
