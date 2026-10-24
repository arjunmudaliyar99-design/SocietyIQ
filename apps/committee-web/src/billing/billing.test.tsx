import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const RUN = {
  id: "r1",
  period_start: "2026-11-01",
  period_end: "2026-11-30",
  bill_date: "2026-11-01",
  due_date: "2026-11-16",
  status: "draft",
  flat_count: 2,
  total_paise: 874000,
  created_by_job: true,
  approved_at: null,
  cancelled_reason: null,
  warnings: [{ key: "flatLeftOut", flat: "C-302", reasons: ["missingCarpetArea"] }],
  draft_flats: [
    { flat_id: "f1", label: "A-101", charges_paise: 420000 },
    { flat_id: "f2", label: "A-305", charges_paise: 454000 },
  ],
  bills: [],
};

const calls: string[] = [];

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    calls.push(`${method} ${path}`);
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
    if (path === "/me")
      return json({ id: "u1", email: "a@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: true, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["treasurer"] }]);
    if (path === "/societies/s1/billing-runs/r1") return json(RUN);
    if (path === "/societies/s1/billing-runs/r1/approve") return json({ ...RUN, status: "approved" });
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

describe("billing run review", () => {
  beforeEach(() => {
    window.localStorage.clear();
    calls.length = 0;
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows warnings and asks before approving", async () => {
    const { container } = renderAt("/bills/runs/r1");
    expect(await screen.findByText("C-302 is left out: no carpet area")).toBeTruthy();
    expect(screen.getByText("₹4,540")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Approve 2 bills" }));
    expect(screen.getByText(/Approve 2 bills for ₹8,740\?/)).toBeTruthy();
    expect(calls).not.toContain("POST /societies/s1/billing-runs/r1/approve");
    fireEvent.click(screen.getByRole("button", { name: "Yes, approve" }));
    await vi.waitFor(() => expect(calls).toContain("POST /societies/s1/billing-runs/r1/approve"));

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id)).toEqual([]);
  });
});
