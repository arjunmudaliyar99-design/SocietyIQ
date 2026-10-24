import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const ENTRY = {
  id: 120,
  created_at: "2026-10-24T09:30:00Z",
  actor_user_id: "u1",
  actor_name: "Treasurer One",
  action: "compliance_item.done",
  entity_type: "compliance_item",
  entity_id: "c1",
  before: { next_due_on: "2026-10-19", title: "Generator service" },
  after: { next_due_on: "2027-01-23", title: "Generator service" },
  reason: null,
};
const OLDER = { ...ENTRY, id: 7, action: "vendor.create", entity_type: "vendor", actor_user_id: null, actor_name: null, before: null, after: { name: "AquaClean" } };

const calls: string[] = [];
let roles = ["auditor"];

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    calls.push(`${init?.method ?? "GET"} ${path}`);
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
    if (path === "/me")
      return json({ id: "u1", email: "a@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: false, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles }]);
    if (path === "/me/consents") return json({ needs_consent: false, granted: [] });
    if (path === "/societies/s1/audit-log") return json({ entries: [ENTRY], next_before_id: 120 });
    if (path === "/societies/s1/audit-log?before_id=120") return json({ entries: [OLDER], next_before_id: null });
    if (path === "/societies/s1/export?format=xlsx") return new Response(new Blob(["PK"]), { status: 200 });
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message_key: "errors.notFound" } }), { status: 404 });
  });
}

function renderAt(path: string) {
  window.localStorage.setItem("societyiq.devToken", JSON.stringify({ token: "t", email: "a@example.com" }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <SettingsProvider>
      <QueryClientProvider client={client}>
        <AuthProvider config={{ apiBaseUrl: "http://api.test", devSignIn: true }}>
          <MemoryRouter initialEntries={[path]}>
            <AppGate allowPassword invite={null} onInviteHandled={() => {}} noSociety={<p>none</p>}>
              <App />
            </AppGate>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    </SettingsProvider>,
  );
}

describe("records: data export and change history", () => {
  beforeEach(() => {
    window.localStorage.clear();
    calls.length = 0;
    roles = ["auditor"];
    vi.stubGlobal("fetch", backend());
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:x"), revokeObjectURL: vi.fn() }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows who changed what, pages older changes, and downloads all data", async () => {
    const { container } = renderAt("/records");
    expect(await screen.findByText("compliance_item.done")).toBeTruthy();
    expect(screen.getByText(/Treasurer One/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Show changes" }));
    expect(screen.getByText("2027-01-23")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Show older changes" }));
    expect(await screen.findByText("vendor.create")).toBeTruthy();
    expect(screen.getByText(/SocietyIQ \(automatic\)/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Download Excel" }));
    await vi.waitFor(() => expect(calls).toContain("GET /societies/s1/export?format=xlsx"));

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id)).toEqual([]);
  }, 20_000);

  it("is not offered to roles without access", async () => {
    roles = ["committee"];
    renderAt("/records");
    expect(await screen.findByText("You do not have permission to do this.")).toBeTruthy();
    expect(calls.some((c) => c.includes("/audit-log"))).toBe(false);
  });
});
