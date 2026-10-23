import { describe, expect, it } from "vitest";

import { colors } from "../colors";
import { contrastRatio } from "./contrast";

// Every text/background pair the components use must pass WCAG AA 4.5:1 (docs/03 §3).
const PAIRS: [string, keyof typeof colors, keyof typeof colors][] = [
  ["body text", "ink", "paper"],
  ["body text on cards", "ink", "surface"],
  ["secondary text", "muted", "paper"],
  ["secondary text on cards", "muted", "surface"],
  ["primary button", "surface", "teal"],
  ["primary button pressed", "surface", "tealDark"],
  ["danger button", "surface", "red"],
  ["links and secondary buttons", "teal", "surface"],
  ["links on page", "teal", "paper"],
  ["error text", "red", "surface"],
  ["paid status", "green", "surface"],
  ["toast text", "surface", "ink"],
  ["toast action", "mint", "ink"],
];

describe("brand palette contrast", () => {
  it.each(PAIRS)("%s (%s on %s) is at least 4.5:1", (_name, fg, bg) => {
    expect(contrastRatio(colors[fg], colors[bg])).toBeGreaterThanOrEqual(4.5);
  });
});
