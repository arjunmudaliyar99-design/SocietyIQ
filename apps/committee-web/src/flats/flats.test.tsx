import { fireEvent, render, screen, within } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const SOCIETY = { id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["admin"] };

const FLATS = [
  { id: "f1", wing_id: "w1", wing_name: "A", flat_number: "101", primary_member: "Member A-101", balance_paise: 0 },
  { id: "f2", wing_id: "w2", wing_name: "B", flat_number: "207", primary_member: "Member B-207", balance_paise: 2940000 },
].map((f) => ({
  ...f,
  carpet_area_sqft: null,
  flat_type: null,
  usage: "residential",
  certified_construction_cost_paise: 96000000,
  water_points: null,
  municipal_property_account: null,
  occupancy: "owner_occupied",
  is_active: true,
}));

const PREVIEW = {
  id: "job1",
  status: "previewed",
  row_count: 2,
  ok_count: 1,
  error_count: 1,
  rows: [
    { row: 2, status: "ok", issues: [], wing: "C", flat_number: "301", owner_name: "Member C-301", opening_balance_paise: 600000 },
    {
      row: 3,
      status: "error",
      issues: [{ key: "phoneDigits", params: { field: "owner_phone", digits: 8 } }],
      wing: "C",
      flat_number: "302",
      owner_name: "Member C-302",
      opening_balance_paise: 1680000,
    },
  ],
};

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
    if (path === "/dev/token") return json({ access_token: "t" });
    if (path === "/me")
      return json({
        id: "u1",
        email: "demo-admin@example.com",
        full_name: null,
        preferred_language: "en",
        text_size: "normal",
        simple_mode: false,
        needs_consent: false,
      });
    if (path === "/me/societies") return json([SOCIETY]);
    if (path === "/societies/s1/flats") return json(FLATS);
    if (path === "/societies/s1/imports" && method === "POST") return json(PREVIEW);
    if (path === "/societies/s1/imports/job1/confirm")
      return json({ ...PREVIEW, status: "imported", rows: PREVIEW.rows });
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message_key: "errors.notFound" } }), {
      status: 404,
    });
  });
}

function renderAt(path: string) {
  window.localStorage.setItem("societyiq.devToken", JSON.stringify({ token: "t", email: "demo-admin@example.com" }));
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

describe("flats", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists flats by wing with the amount due", async () => {
    renderAt("/flats");
    expect(await screen.findByRole("heading", { name: "Wing B" })).toBeTruthy();
    const b207 = screen.getByRole("link", { name: /B-207/ });
    expect(within(b207).getByText("₹29,400")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Import from Excel" })).toBeTruthy();
  });

  it("previews an import in plain words and has no serious axe issues", async () => {
    const { container } = renderAt("/flats/import");
    expect(await screen.findByRole("heading", { name: "Import flats from Excel" })).toBeTruthy();
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["x"], "flats.xlsx");
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText("Owner phone has 8 digits; it needs 10.")).toBeTruthy();
    expect(screen.getByText(/Row 3: Needs fixing/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Import 1 flats" })).toBeTruthy();

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    const serious = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => v.id)).toEqual([]);
  });
});
