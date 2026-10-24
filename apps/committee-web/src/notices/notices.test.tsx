import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const DRAFT = {
  id: "n1",
  title: "Water tank cleaning",
  body: "Sunday 10 to 2. Please store water.",
  language: "en",
  audience: "all",
  audience_wing_id: null,
  status: "draft",
  ai_assisted: true,
  published_at: null,
  created_at: "2026-10-24T09:00:00Z",
  updated_at: "2026-10-24T09:00:00Z",
  is_read: false,
  translations: {},
  can_edit: true,
  can_publish: true,
  read_count: 0,
  recipient_count: 118,
  emails_sent: 0,
  emails_failed: 0,
};

const calls: { method: string; path: string; body: unknown }[] = [];

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : null;
    calls.push({ method, path, body });
    const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status });
    if (path === "/me")
      return json({ id: "u1", email: "a@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: true, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["admin"] }]);
    if (path === "/societies/s1/wings") return json([{ id: "w1", name: "A", has_lift: true }]);
    if (path === "/societies/s1/notices/options") return json({ ai_available: true, whatsapp_available: false });
    if (path === "/societies/s1/notices/ai-draft")
      return json({ title: "Water tank cleaning", body: "Sunday 10 to 2. Please store water." });
    if (path === "/societies/s1/notices" && method === "POST") return json(DRAFT, 201);
    if (path === "/societies/s1/notices/n1/publish")
      return json({ ...DRAFT, status: "published", can_edit: false, can_publish: false, published_at: "2026-10-24T10:00:00Z", emails_sent: 118 });
    if (path === "/societies/s1/notices/n1") return json(DRAFT);
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

async function seriousViolations(container: Element) {
  const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  return result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id);
}

describe("committee notices (docs/02 §9)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    calls.length = 0;
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("Help me write fills the form; saving keeps it a draft", async () => {
    const { container } = renderAt("/notices/new");
    fireEvent.change(await screen.findByLabelText("Your notes"), { target: { value: "tank cleaning sunday" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Help me write" })[0]);
    expect(await screen.findByText(/written with AI help/)).toBeTruthy();
    expect((screen.getByLabelText("Title") as HTMLInputElement).value).toBe("Water tank cleaning");

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await vi.waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/societies/s1/notices")).toBe(true));
    expect(calls.find((c) => c.method === "POST" && c.path === "/societies/s1/notices")?.body).toMatchObject({
      title: "Water tank cleaning",
      ai_assisted: true,
    });
    // Nothing is published by the helper or by saving.
    expect(calls.some((c) => c.path.endsWith("/publish"))).toBe(false);
    expect(await seriousViolations(container)).toEqual([]);
  });

  it("asks before publishing and says how many people get the email", async () => {
    const { container } = renderAt("/notices/n1");
    fireEvent.click(await screen.findByRole("button", { name: "Publish" }));
    expect(screen.getByText("Publish this notice and email it to 118 people?")).toBeTruthy();
    expect(calls.some((c) => c.path.endsWith("/publish"))).toBe(false);
    expect(screen.getByText(/WhatsApp · Coming soon/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Yes, publish" }));
    await vi.waitFor(() => expect(calls.some((c) => c.path === "/societies/s1/notices/n1/publish")).toBe(true));
    expect(await seriousViolations(container)).toEqual([]);
  });
});
