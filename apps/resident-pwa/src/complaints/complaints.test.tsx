import { fireEvent, render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import { ComplaintPage, ReportPage } from "./ComplaintPages";

const DETAIL = {
  id: "c1",
  flat_id: "f1",
  flat_label: "B-207",
  raised_on_behalf: false,
  category: "lift",
  location: "common_area",
  description: null,
  status: "resolved",
  assigned_to_text: null,
  resident_feedback: null,
  created_at: "2026-10-20T09:00:00Z",
  updated_at: "2026-10-20T09:00:00Z",
  resolved_at: "2026-10-22T09:00:00Z",
  closed_at: null,
  photo_ids: [],
  can_manage: false,
  updates: [],
};

const calls: { method: string; path: string; body: unknown }[] = [];

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : init?.body ?? null;
    calls.push({ method, path, body });
    const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status });
    if (path === "/me")
      return json({ id: "u1", email: "r@example.com", full_name: null, preferred_language: "en", text_size: "normal", simple_mode: true, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["owner"] }]);
    if (path === "/societies/s1/complaints" && method === "POST") return json({ ...DETAIL, status: "open" }, 201);
    if (path === "/societies/s1/complaints/c1/photos") return json({ ...DETAIL, status: "open" }, 201);
    if (path === "/societies/s1/complaints/c1/feedback") return json({ ...DETAIL, status: "closed", resident_feedback: "fixed" });
    if (path === "/societies/s1/complaints/c1") return json(DETAIL);
    return json({ error: { code: "NOT_FOUND", message_key: "errors.notFound" } }, 404);
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
              <Routes>
                <Route path="/report" element={<ReportPage />} />
                <Route path="/complaints/:complaintId" element={<ComplaintPage />} />
              </Routes>
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

describe("report a problem (docs/02 §8)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    calls.length = 0;
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("asks for a category, then sends with the photo", async () => {
    const { container } = renderAt("/report");
    const send = await screen.findByRole("button", { name: "Send" });
    expect(send.className).toContain("min-h-[56px]");
    fireEvent.click(send);
    expect(screen.getByText("Choose what the problem is")).toBeTruthy();
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Lift" }));
    fireEvent.click(screen.getByRole("button", { name: "Common area" }));
    const photo = new File([new Uint8Array([0xff, 0xd8, 0xff])], "IMG_1.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Add a photo"), { target: { files: [photo] } });
    expect(screen.getByText("Photo added")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await vi.waitFor(() => expect(calls.map((c) => c.path)).toContain("/societies/s1/complaints/c1/photos"));
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      category: "lift",
      location: "common_area",
      flat_id: null,
      description: null,
    });
    expect(await seriousViolations(container)).toEqual([]);
  });

  it("after Resolved the resident answers Fixed or Not fixed", async () => {
    const { container } = renderAt("/complaints/c1");
    expect(await screen.findByText("Is the problem fixed?")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Yes, fixed" }));
    await vi.waitFor(() =>
      expect(calls.find((c) => c.path.endsWith("/feedback"))?.body).toEqual({ feedback: "fixed" }),
    );
    expect(await seriousViolations(container)).toEqual([]);
  });
});
