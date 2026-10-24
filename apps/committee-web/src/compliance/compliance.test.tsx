import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const ITEM = {
  id: "c1",
  item_type: "generator_service",
  title: "Generator service",
  vendor_id: "v1",
  vendor_name: "Powergen Services",
  last_done_on: null,
  next_due_on: "2026-10-19",
  repeat_months: 3,
  contract_value_paise: null,
  notes: null,
  is_active: true,
  status: "overdue",
  days_left: -5,
};
const TANK = { ...ITEM, id: "c2", item_type: "tank_cleaning", title: "Water tank cleaning", vendor_name: "AquaClean", status: "due_soon", days_left: 12, next_due_on: "2026-11-05" };

const HOME = {
  coming_soon: [],
  open_complaints: 3,
  collected_paise: 13100000,
  collected_count: 31,
  outstanding_paise: 7560000,
  flats_with_dues: 6,
  payments_waiting: 2,
  compliance_overdue: 1,
  compliance_due_soon: 2,
  next_bill_date: "2026-11-01",
  latest_run: null,
  attention: [{ key: "home.attention.overdue", params: { title: "Generator service", days: 5 }, link: "/compliance/c1" }],
};

const calls: string[] = [];

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    calls.push(`${method} ${path}`);
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
    if (path === "/me")
      return json({ id: "u1", email: "a@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: false, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["committee"] }]);
    if (path === "/societies/s1/home") return json(HOME);
    if (path === "/societies/s1/compliance/items") return json([ITEM, TANK]);
    if (path === "/societies/s1/compliance/items/c1") return json({ ...ITEM, events: [] });
    if (path === "/societies/s1/compliance/items/c1/done")
      return json({ ...ITEM, status: "ok", days_left: 85, next_due_on: "2027-01-23", events: [{ id: "e1", done_on: "2026-10-23", notes: null }] });
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

async function noSeriousAxe(container: HTMLElement) {
  const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  expect(result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id)).toEqual([]);
}

describe("committee home and compliance", () => {
  beforeEach(() => {
    window.localStorage.clear();
    calls.length = 0;
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("home shows coming-soon cards, compliance counts and the attention list", async () => {
    const { container } = renderAt("/");
    expect(await screen.findByText("Compliance due soon")).toBeTruthy();
    expect(screen.getByText("1 overdue")).toBeTruthy();
    expect(screen.queryByText("Coming soon")).toBeNull();
    expect(screen.getByText("₹1,31,000")).toBeTruthy();
    expect(screen.getByText("6 flats with dues")).toBeTruthy();
    expect(screen.getByText("Open complaints")).toBeTruthy();
    expect(screen.getByText("Generator service is 5 days overdue")).toBeTruthy();
    await noSeriousAxe(container);
  });

  it("lists items with words for status, and asks before marking done", async () => {
    const list = renderAt("/compliance");
    expect(await screen.findByText("Generator service")).toBeTruthy();
    expect(screen.getByText("Overdue")).toBeTruthy();
    expect(screen.getByText("Due soon")).toBeTruthy();
    await noSeriousAxe(list.container);
    list.unmount();

    renderAt("/compliance/c1");
    fireEvent.click(await screen.findByRole("button", { name: "Mark as done" }));
    expect(screen.getByText(/Mark Generator service as done on/)).toBeTruthy();
    expect(calls).not.toContain("POST /societies/s1/compliance/items/c1/done");
    const buttons = screen.getAllByRole("button", { name: "Mark as done" });
    fireEvent.click(buttons[buttons.length - 1] as HTMLElement);
    await vi.waitFor(() => expect(calls).toContain("POST /societies/s1/compliance/items/c1/done"));
  });
});
