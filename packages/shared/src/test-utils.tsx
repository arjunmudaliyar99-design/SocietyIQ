import { render, type RenderResult } from "@testing-library/react";
import axe from "axe-core";
import type { ReactElement } from "react";

import { SettingsProvider } from "./settings";

export function renderWithSettings(ui: ReactElement): RenderResult {
  return render(<SettingsProvider>{ui}</SettingsProvider>);
}

/** Serious or critical axe violations. jsdom cannot compute colour contrast; see contrast tests. */
export async function seriousAxeViolations(container: Element): Promise<string[]> {
  const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  return result.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id}: ${v.help}`);
}
