import { describe, expect, it } from "vitest";

import { LANGUAGES, NAMESPACES, resources } from "./i18n";

function keys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value).flatMap(([k, v]) =>
    k === "_status" ? [] : keys(v, prefix ? `${prefix}.${k}` : k),
  );
}

function values(value: unknown): unknown[] {
  if (typeof value !== "object" || value === null) return [value];
  return Object.values(value).flatMap(values);
}

describe("translations (docs/03 §7)", () => {
  it("has all five languages", () => {
    expect(LANGUAGES.map((l) => l.code)).toEqual(["en", "mr", "hi", "gu", "ta"]);
  });

  for (const ns of NAMESPACES) {
    const english = keys(resources.en[ns]).sort();

    for (const { code } of LANGUAGES.filter((l) => l.code !== "en")) {
      it(`${code}/${ns} has exactly the English keys and is marked draft`, () => {
        const file = resources[code][ns] as Record<string, unknown>;
        expect(keys(file).sort()).toEqual(english);
        expect(file._status).toBe("draft");
      });
    }

    it(`en/${ns} has no empty strings`, () => {
      expect(values(resources.en[ns]).every((v) => typeof v === "string" && v.length > 0)).toBe(true);
    });
  }
});
