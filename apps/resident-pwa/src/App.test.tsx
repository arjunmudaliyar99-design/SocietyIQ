import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { SettingsProvider } from "@societyiq/shared";

import App from "./App";

function renderApp(path = "/") {
  return render(
    <SettingsProvider>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </SettingsProvider>,
  );
}

describe("resident home (docs/02 §11)", () => {
  it("shows the dues banner and three big buttons", () => {
    renderApp();
    expect(screen.getByText(/Your dues will show here/)).toBeTruthy();
    for (const name of ["Pay", "Notices", "Report a problem"]) {
      expect(screen.getByRole("button", { name }).className).toContain("min-h-[56px]");
    }
  });

  it("each big button opens its page with a way back", () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: "Pay" }));
    expect(screen.getByRole("heading", { name: "Pay" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Go back" }));
    expect(screen.getByRole("button", { name: "Report a problem" })).toBeTruthy();
  });

  it("menu lists the other screens", () => {
    renderApp("/menu");
    for (const name of ["My bills", "My receipts", "My complaints", "Language and text size"]) {
      expect(screen.getByRole("button", { name })).toBeTruthy();
    }
  });

  it("language switch changes the visible text", () => {
    renderApp();
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "gu" } });
    expect(screen.getByRole("button", { name: "ચૂકવો" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Pay" })).toBeNull();
  });

  it("text size setting is on the settings page", () => {
    renderApp("/settings");
    fireEvent.click(screen.getByRole("button", { name: "Large" }));
    expect(document.documentElement.style.getPropertyValue("--siq-root-size")).toBe("21px");
  });

  it("has no serious axe violations", async () => {
    for (const path of ["/", "/menu", "/settings"]) {
      const { container, unmount } = renderApp(path);
      const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
      const serious = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => v.id)).toEqual([]);
      unmount();
    }
  });
});
