import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const STANDARD = [
  { standard_code: "service", calc_type: "equal_per_flat", applies_to: "all", rule: "Rule 106C-12", legal_percent: null, legal_percent_kind: null, legal_source: null },
  {
    standard_code: "non_occupancy",
    calc_type: "pct_of_head",
    applies_to: "let_out_only",
    rule: "Rule 106C-12",
    legal_percent: "10",
    legal_percent_kind: "fixed",
    legal_source: "MCS Rules 106C-12 (2026)",
  },
];

const SERVICE = {
  id: "h1",
  name: "Service charges",
  code: "service",
  standard_code: "service",
  calc_type: "equal_per_flat",
  period_total_paise: 40800000,
  fixed_amount_paise: null,
  percent: null,
  percent_of_head_id: null,
  applies_to: "all",
  gb_resolution_ref: null,
  gb_resolution_date: null,
  method_deviation_reason: null,
  frequency: "every_bill",
  one_time_period: null,
  sort_order: 1,
  is_active: true,
  approved_at: null,
};

const PREVIEW = {
  period_start: "2026-11-01",
  period_end: "2026-11-30",
  heads: [{ id: "h1", name: "Service charges", total_paise: 680000 }],
  flats: [
    { flat_id: "f1", label: "A-101", lines: { h1: 340000 }, charges_paise: 340000, rounding_paise: 0, total_paise: 340000, overridden: [], warnings: [] },
    { flat_id: "f2", label: "A-305", lines: { h1: 340000 }, charges_paise: 340000, rounding_paise: 0, total_paise: 340000, overridden: [], warnings: [] },
  ],
  excluded: [{ flat_id: "f3", label: "B-207", reasons: ["missingCarpetArea"] }],
  total_paise: 680000,
  missing: { carpet_area: 12, construction_cost: 0, water_points: 3, no_member: 0 },
};

let lastBody: unknown = null;

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "").split("?")[0];
    const method = init?.method ?? "GET";
    const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
    if (path === "/me")
      return json({ id: "u1", email: "a@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: false, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["admin"] }]);
    if (path === "/societies/s1/charges/standard-heads") return json(STANDARD);
    if (path === "/societies/s1/charges/heads" && method === "GET") return json([SERVICE]);
    if (path === "/societies/s1/charges/heads" && method === "POST") {
      lastBody = JSON.parse(String(init?.body));
      return json(
        {
          error: {
            code: "LEGAL_BLOCK",
            message_key: "errors.legalBlock",
            details: [{ level: "block", key: "nonOccupancyPercent", params: { required: "10", rule: "MCS Rules 106C-12 (2026)" } }],
          },
        },
        422,
      );
    }
    if (path === "/societies/s1/charges/preview") return json(PREVIEW);
    return json({ error: { code: "NOT_FOUND", message_key: "errors.notFound" } }, 404);
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

async function seriousAxe(container: HTMLElement) {
  const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  return result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id);
}

describe("charges", () => {
  beforeEach(() => {
    window.localStorage.clear();
    lastBody = null;
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("preview shows amounts, flats left out and missing data in plain words", async () => {
    const { container } = renderAt("/charges/preview");
    expect(await screen.findByText("12 flats have no carpet area yet")).toBeTruthy();
    expect(screen.getByText("3 flats have no number of water taps yet")).toBeTruthy();
    expect(screen.queryByText(/no construction cost yet/)).toBeNull();
    expect(screen.getByText(/no carpet area$/)).toBeTruthy();
    expect(screen.getAllByText("₹3,400").length).toBeGreaterThan(0);
    expect(await seriousAxe(container)).toEqual([]);
  });

  it("non-occupancy takes its percent from the API and shows the rule when refused", async () => {
    const { container } = renderAt("/charges/new");
    fireEvent.click(await screen.findByRole("button", { name: /Non-occupancy charges/ }));
    expect(screen.getByText(/Fixed at 10% of the flat's service charges/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Save charge" }));
    expect(await screen.findByText(/must be exactly 10% of service charges/)).toBeTruthy();
    expect(screen.getByText("Source: MCS Rules 106C-12 (2026)")).toBeTruthy();
    expect(lastBody).toMatchObject({ standard_code: "non_occupancy", percent: "10", percent_of_head_id: "h1", applies_to: "let_out_only" });
    expect(await seriousAxe(container)).toEqual([]);
  });
});
