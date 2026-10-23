import { describe, expect, it } from "vitest";

import { formatPaise } from "./money";

describe("formatPaise (docs/03 §6)", () => {
  it.each([
    [13100000, "₹1,31,000"],
    [420000, "₹4,200"],
    [0, "₹0"],
    [1050, "₹10.50"],
    [1, "₹0.01"],
    [123456789, "₹12,34,567.89"],
    [-50000, "-₹500"],
  ])("%i paise -> %s", (paise, expected) => {
    expect(formatPaise(paise)).toBe(expected);
  });

  it("rejects non-integer amounts instead of rounding silently", () => {
    expect(() => formatPaise(10.5)).toThrow();
  });
});
