import { describe, expect, it } from "vitest";

import { flatLabel, paiseToRupeesInput, rupeesToPaise } from "./labels";

describe("flat labels", () => {
  it("adds the wing only when there are several", () => {
    expect(flatLabel({ wing_name: "B", flat_number: "207" }, 4)).toBe("B-207");
    expect(flatLabel({ wing_name: "Main", flat_number: "301" }, 1)).toBe("301");
  });
});

describe("rupees and paise", () => {
  it("reads rupees without floating point", () => {
    expect(rupeesToPaise("9,60,000")).toBe(96000000);
    expect(rupeesToPaise("₹ 4200.5")).toBe(420050);
    expect(rupeesToPaise("0.1")).toBe(10);
    expect(rupeesToPaise("12.345")).toBeNull();
    expect(rupeesToPaise("-5")).toBeNull();
    expect(rupeesToPaise("abc")).toBeNull();
  });

  it("writes paise back for editing", () => {
    expect(paiseToRupeesInput(96000000)).toBe("960000");
    expect(paiseToRupeesInput(420050)).toBe("4200.50");
    expect(paiseToRupeesInput(null)).toBe("");
  });
});
