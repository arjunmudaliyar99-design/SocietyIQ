import { fireEvent, render, screen, within } from "@testing-library/react";
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

function navLinks() {
  return within(screen.getByRole("navigation", { name: "Main menu" })).getAllByRole("link");
}

describe("committee shell", () => {
  it("shows the logo, society name and top-bar actions", () => {
    renderApp();
    expect(screen.getByAltText("SocietyIQ")).toBeTruthy();
    expect(screen.getByText("Your society")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Help" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Account" })).toBeTruthy();
    expect(screen.getByLabelText("Language")).toBeTruthy();
  });

  it("Simple view shows exactly 5 menu items; Detailed view shows more", () => {
    renderApp();
    expect(navLinks()).toHaveLength(5);
    fireEvent.click(screen.getByRole("button", { name: "Account" }));
    fireEvent.click(screen.getByRole("button", { name: "Detailed view" }));
    expect(navLinks()).toHaveLength(10);
  });

  it("language switch changes the visible text", () => {
    renderApp();
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "hi" } });
    const nav = screen.getByRole("navigation", { name: "मुख्य मेनू" });
    expect(within(nav).getByText("बकाया")).toBeTruthy();
    expect(screen.queryByText("Dues")).toBeNull();
    expect(screen.getByRole("button", { name: "मदद" })).toBeTruthy();
  });

  it("menu pages say Coming soon", () => {
    renderApp("/dues");
    expect(screen.getByRole("heading", { name: "Dues" })).toBeTruthy();
    expect(screen.getByText(/Coming soon/)).toBeTruthy();
  });

  it("component preview renders", () => {
    renderApp("/preview");
    expect(screen.getByRole("heading", { name: "Component preview" })).toBeTruthy();
  });

  it("has no serious axe violations on home and preview", async () => {
    for (const path of ["/", "/preview"]) {
      const { container, unmount } = renderApp(path);
      const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
      const serious = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => v.id)).toEqual([]);
      unmount();
    }
  });
});
