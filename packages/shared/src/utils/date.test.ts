import { describe, expect, it } from "vitest";

import { formatDate } from "./date";

describe("formatDate (docs/03 §6)", () => {
  it("formats English as 25 Sep 2026", () => {
    expect(formatDate("2026-09-25")).toBe("25 Sep 2026");
    expect(formatDate(new Date(2026, 0, 5))).toBe("5 Jan 2026");
  });

  it("does not shift calendar dates across timezones", () => {
    expect(formatDate("2026-03-01")).toBe("1 Mar 2026");
  });

  it("uses localised month names for other languages", () => {
    const text = formatDate("2026-09-25", "hi");
    expect(text).toContain("2026");
    expect(text).not.toContain("Sep");
  });

  it("rejects text that is not an ISO date", () => {
    expect(() => formatDate("25/09/2026")).toThrow();
  });
});
