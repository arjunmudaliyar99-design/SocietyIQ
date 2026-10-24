import { render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const OWNER_FLAT = {
  flat_id: "f1",
  label: "B-207",
  role: "owner",
  can_pay: true,
  balance_paise: 420000,
  months_pending: 1,
  latest_bill: { id: "b1", bill_number: "B/2026-27/000045", total_due_paise: 420000, due_date: "2026-11-16", status: "issued" },
  pending_reports: 0,
  pay: {
    amount_paise: 420000,
    upi_id: "shantisadan@examplebank",
    payee: "Shanti Sadan CHS",
    upi_link: "upi://pay?pa=shantisadan@examplebank&am=4200.00&cu=INR",
    qr_data_uri: "data:image/png;base64,AAAA",
  },
};

const TENANT_FLAT = { ...OWNER_FLAT, role: "tenant", can_pay: false, balance_paise: null, months_pending: null, latest_bill: null, pay: null };

function backend(flats: unknown[]) {
  return vi.fn(async (url: string) => {
    const path = url.replace("http://api.test/api/v1", "");
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
    if (path === "/me")
      return json({ id: "u1", email: "r@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: true, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["owner"] }]);
    if (path === "/societies/s1/my/flats") return json(flats);
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message_key: "errors.notFound" } }), { status: 404 });
  });
}

function renderAt(path: string) {
  window.localStorage.setItem("societyiq.devToken", JSON.stringify({ token: "t", email: "r@example.com" }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <SettingsProvider>
      <QueryClientProvider client={client}>
        <AuthProvider config={{ apiBaseUrl: "http://api.test", devSignIn: true }}>
          <MemoryRouter initialEntries={[path]}>
            <AppGate allowPassword={false} invite={null} onInviteHandled={() => {}} noSociety={<p>none</p>}>
              <App />
            </AppGate>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    </SettingsProvider>,
  );
}

describe("resident money (docs/07 M7)", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("owner sees the dues banner and Pay", async () => {
    vi.stubGlobal("fetch", backend([OWNER_FLAT]));
    const { container } = renderAt("/");
    expect(await screen.findByText("Flat B-207")).toBeTruthy();
    expect(screen.getByText("₹4,200")).toBeTruthy();
    expect(screen.getByText("Pay by 16 Nov 2026")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Pay" })).toBeTruthy();
    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id)).toEqual([]);
  });

  it("pay page shows the UPI deep link and the I have paid form", async () => {
    vi.stubGlobal("fetch", backend([OWNER_FLAT]));
    renderAt("/pay");
    const link = await screen.findByRole("link", { name: "Open UPI app" });
    expect(link.getAttribute("href")).toContain("upi://pay?pa=shantisadan@examplebank");
    expect(screen.getByRole("img", { name: "UPI QR code to pay Shanti Sadan CHS" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "I have paid" })).toBeTruthy();
  });

  it("a tenant the owner has not allowed sees no Pay button", async () => {
    vi.stubGlobal("fetch", backend([TENANT_FLAT]));
    renderAt("/");
    expect(await screen.findByText("Bills for this flat go to the owner.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Pay" })).toBeNull();
  });
});
