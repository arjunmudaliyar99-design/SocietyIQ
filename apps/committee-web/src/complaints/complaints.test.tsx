import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import App from "../App";

const COMPLAINT = {
  id: "c1",
  flat_id: "f1",
  flat_label: "B-207",
  raised_on_behalf: false,
  category: "water",
  location: "my_flat",
  description: "Leak under the kitchen sink",
  status: "open",
  assigned_to_text: null,
  resident_feedback: null,
  created_at: "2026-10-20T09:00:00Z",
  updated_at: "2026-10-20T09:00:00Z",
  resolved_at: null,
  closed_at: null,
};
const DETAIL = {
  ...COMPLAINT,
  photo_ids: [],
  can_manage: true,
  updates: [
    { id: "u1", message: "Plumber told", new_status: null, visible_to_resident: false, created_at: "2026-10-21T09:00:00Z" },
  ],
};

const calls: { method: string; path: string; body: unknown }[] = [];

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : null;
    calls.push({ method, path, body });
    const json = (b: unknown) => new Response(JSON.stringify(b), { status: 200 });
    if (path === "/me")
      return json({ id: "u1", email: "a@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: true, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["committee"] }]);
    if (path === "/societies/s1/complaints?status=open") return json([COMPLAINT]);
    if (path === "/societies/s1/complaints?status=closed") return json([]);
    if (path === "/societies/s1/complaints/c1") return json(DETAIL);
    if (path === "/societies/s1/complaints/c1/updates")
      return json({ ...DETAIL, status: "in_progress", updates: [...DETAIL.updates, { id: "u2", message: body.message, new_status: "in_progress", visible_to_resident: true, created_at: "2026-10-22T09:00:00Z" }] });
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

async function seriousViolations(container: Element) {
  const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  return result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id);
}

describe("committee complaints (docs/02 §8)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    calls.length = 0;
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists open complaints first and filters by status", async () => {
    const { container } = renderAt("/complaints");
    expect(await screen.findByText("Water / leak")).toBeTruthy();
    expect(screen.getByText(/B-207/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open" }).getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "Closed" }));
    expect(await screen.findByText("No complaints with this status.")).toBeTruthy();
    expect(calls.map((c) => c.path)).toContain("/societies/s1/complaints?status=closed");
    expect(await seriousViolations(container)).toEqual([]);
  });

  it("posts an update with a status change and marks committee-only notes", async () => {
    const { container } = renderAt("/complaints/c1");
    expect(await screen.findByText("Leak under the kitchen sink")).toBeTruthy();
    expect(screen.getByText(/Committee only/)).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Plumber coming Monday" } });
    fireEvent.change(screen.getByLabelText("Change status to"), { target: { value: "in_progress" } });
    fireEvent.click(screen.getByRole("button", { name: "Post update" }));

    await vi.waitFor(() =>
      expect(calls.find((c) => c.path === "/societies/s1/complaints/c1/updates")?.body).toEqual({
        message: "Plumber coming Monday",
        new_status: "in_progress",
        visible_to_resident: true,
      }),
    );
    expect(await seriousViolations(container)).toEqual([]);
  });
});
