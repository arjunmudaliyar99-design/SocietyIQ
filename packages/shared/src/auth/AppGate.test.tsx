import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsProvider } from "../settings";
import { seriousAxeViolations } from "../test-utils";
import { AppGate } from "./AppGate";
import { AuthProvider } from "./AuthProvider";
import { useCurrentSociety } from "./society-context";

interface FakeServer {
  needsConsent: boolean;
  societies: { id: string; name: string; city: string | null; roles: string[] }[];
  calls: string[];
}

function fakeBackend(server: FakeServer) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api.test/api/v1", "");
    const method = init?.method ?? "GET";
    server.calls.push(`${method} ${path}`);
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
    if (path === "/dev/token") return json({ access_token: "dev-token" });
    if (path === "/me")
      return json({
        id: "u1",
        email: "a@example.com",
        full_name: null,
        preferred_language: "en",
        text_size: "normal",
        simple_mode: true,
        needs_consent: server.needsConsent,
      });
    if (path === "/me/consents" && method === "POST") {
      server.needsConsent = false;
      return json({ policy_version: "v", needs_consent: false, granted: [] });
    }
    if (path === "/me/societies") return json(server.societies);
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message_key: "errors.notFound" } }), {
      status: 404,
    });
  });
}

function SocietyName() {
  return <p>Inside: {useCurrentSociety()?.society.name}</p>;
}

function renderGate() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <SettingsProvider>
      <QueryClientProvider client={client}>
        <AuthProvider config={{ apiBaseUrl: "http://api.test", devSignIn: true }}>
          <AppGate allowPassword invite={null} onInviteHandled={() => {}} noSociety={<p>No society yet</p>}>
            <SocietyName />
          </AppGate>
        </AuthProvider>
      </QueryClientProvider>
    </SettingsProvider>,
  );
}

async function signIn() {
  fireEvent.change(screen.getByLabelText("Your email address"), { target: { value: "a@example.com" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("AppGate", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("goes sign-in → consent → the only society", async () => {
    const server: FakeServer = {
      needsConsent: true,
      societies: [{ id: "s1", name: "Shanti Sadan CHS", city: "Mumbai", roles: ["admin"] }],
      calls: [],
    };
    vi.stubGlobal("fetch", fakeBackend(server));
    const { container } = renderGate();

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeTruthy();
    expect(await seriousAxeViolations(container)).toEqual([]);
    await signIn();

    expect(await screen.findByRole("heading", { name: "Before you start" })).toBeTruthy();
    expect(await seriousAxeViolations(container)).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByRole("alert").textContent).toContain("tick the box");
    fireEvent.click(screen.getByLabelText("I agree to the terms of use and the privacy policy"));
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByText("Inside: Shanti Sadan CHS")).toBeTruthy();
    expect(server.calls).toContain("POST /me/consents");
  });

  it("asks which society when there are several", async () => {
    const server: FakeServer = {
      needsConsent: false,
      societies: [
        { id: "s1", name: "Gulmohar Heights CHS", city: "Thane", roles: ["treasurer"] },
        { id: "s2", name: "Sagar Darshan CHS", city: "Mumbai", roles: ["admin"] },
      ],
      calls: [],
    };
    vi.stubGlobal("fetch", fakeBackend(server));
    renderGate();
    await signIn();

    fireEvent.click(await screen.findByRole("button", { name: "Sagar Darshan CHS, Mumbai" }));
    expect(await screen.findByText("Inside: Sagar Darshan CHS")).toBeTruthy();
  });

  it("shows the no-society screen", async () => {
    vi.stubGlobal("fetch", fakeBackend({ needsConsent: false, societies: [], calls: [] }));
    renderGate();
    await signIn();
    await waitFor(() => expect(screen.getByText("No society yet")).toBeTruthy());
  });

  it("checks the email before signing in", async () => {
    vi.stubGlobal("fetch", fakeBackend({ needsConsent: false, societies: [], calls: [] }));
    renderGate();
    fireEvent.change(screen.getByLabelText("Your email address"), { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/Check the email address/)).toBeTruthy();
  });
});
