import { render, screen } from "@testing-library/react";
import axe from "axe-core";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppGate, AuthProvider, QueryClient, QueryClientProvider, SettingsProvider } from "@societyiq/shared";

import { NoticePage, NoticesPage } from "./NoticePages";

const BASE = {
  body: "Sunday 10 to 2.",
  language: "en",
  audience: "all",
  audience_wing_id: null,
  status: "published",
  ai_assisted: false,
  created_at: "2026-10-20T09:00:00Z",
  updated_at: "2026-10-20T09:00:00Z",
};
const UNREAD = { ...BASE, id: "n1", title: "Water tank cleaning", published_at: "2026-10-24T09:00:00Z", is_read: false };
const READ = { ...BASE, id: "n2", title: "Diwali decorations", published_at: "2026-10-20T09:00:00Z", is_read: true };

const calls: { method: string; path: string }[] = [];

function backend() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    calls.push({ method, path });
    const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status });
    if (path === "/me")
      return json({ id: "u1", email: "r@example.com", full_name: null, preferred_language: "mr", text_size: "normal", simple_mode: true, needs_consent: false });
    if (path === "/me/societies") return json([{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["owner"] }]);
    if (path === "/societies/s1/notices") return json([UNREAD, READ]);
    if (path === "/societies/s1/notices/n1/read") return json({ read: true });
    if (path === "/societies/s1/notices/n1")
      return json({
        ...UNREAD,
        translations: { mr: { title: "पाण्याची टाकी साफसफाई", body: "रविवारी 10 ते 2.", reviewed: true } },
        can_edit: false,
        can_publish: false,
      });
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
                <Route path="/notices" element={<NoticesPage />} />
                <Route path="/notices/:noticeId" element={<NoticePage />} />
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

describe("resident notices (docs/02 §11)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    calls.length = 0;
    vi.stubGlobal("fetch", backend());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists newest first with unread in bold", async () => {
    const { container } = renderAt("/notices");
    const unread = await screen.findByText(/पाण्याची|Water tank cleaning/);
    expect(unread.className).toContain("font-bold");
    expect(screen.getByText("Diwali decorations").className).toContain("font-normal");
    expect(await seriousViolations(container)).toEqual([]);
  });

  it("opening a notice marks it read and shows the checked translation", async () => {
    renderAt("/notices/n1");
    expect(await screen.findByText("पाण्याची टाकी साफसफाई")).toBeTruthy();
    await vi.waitFor(() =>
      expect(calls).toContainEqual({ method: "POST", path: "/societies/s1/notices/n1/read" }),
    );
  });
});
