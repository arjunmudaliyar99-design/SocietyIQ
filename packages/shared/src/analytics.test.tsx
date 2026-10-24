import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const posthog = vi.hoisted(() => ({
  init: vi.fn(),
  identify: vi.fn(),
  opt_in_capturing: vi.fn(),
  opt_out_capturing: vi.fn(),
  reset: vi.fn(),
  startSessionRecording: vi.fn(),
  stopSessionRecording: vi.fn(),
}));
const state = vi.hoisted(() => ({ consents: ["terms", "privacy"] as string[], roles: ["treasurer"] as string[] }));

vi.mock("posthog-js", () => ({ default: posthog }));
vi.mock("./api/hooks", () => ({
  queryKeys: { me: ["me"] },
  useMe: () => ({ data: { id: "3f1c0f9e-0000-4000-8000-000000000001", email: "a@example.com" } }),
}));
vi.mock("./auth/auth-context", () => ({ useAuth: () => ({ api: {}, status: "signedIn" }) }));
vi.mock("./auth/society-context", () => ({
  useCurrentSociety: () => ({ society: { id: "s1", roles: state.roles } }),
}));
vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({ data: { granted: state.consents.map((purpose) => ({ purpose })) } }),
  useMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useQueryClient: () => ({}),
}));

import { AnalyticsTracker } from "./analytics";
import { analyticsAllowed } from "./analytics-gate";

describe("analytics gate (docs/04 §10)", () => {
  it("needs a key, a non-local environment and consent", () => {
    expect(analyticsAllowed({}, true)).toBe(false);
    expect(analyticsAllowed({ key: "k", env: "local" }, true)).toBe(false);
    expect(analyticsAllowed({ key: "k" }, true)).toBe(false);
    expect(analyticsAllowed({ key: "k", env: "production" }, false)).toBe(false);
    expect(analyticsAllowed({ key: "k", env: "production" }, true)).toBe(true);
  });
});

describe("AnalyticsTracker", () => {
  beforeEach(() => {
    Object.values(posthog).forEach((f) => f.mockClear());
    state.consents = ["terms", "privacy"];
    state.roles = ["treasurer"];
  });

  it("loads nothing without a key", async () => {
    state.consents = ["terms", "privacy", "analytics"];
    render(<AnalyticsTracker config={{ env: "production" }} />);
    await new Promise((r) => setTimeout(r, 0));
    expect(posthog.init).not.toHaveBeenCalled();
  });

  it("loads nothing without consent", async () => {
    render(<AnalyticsTracker config={{ key: "k", env: "production" }} />);
    await new Promise((r) => setTimeout(r, 0));
    expect(posthog.init).not.toHaveBeenCalled();
  });

  it("with consent: masks everything, sends only the user id, records admins only", async () => {
    state.consents = ["terms", "privacy", "analytics"];
    render(<AnalyticsTracker config={{ key: "k", env: "production" }} />);
    await vi.waitFor(() => expect(posthog.identify).toHaveBeenCalled());
    const [, options] = posthog.init.mock.calls[0] as [string, Record<string, unknown>];
    expect(options).toMatchObject({
      mask_all_text: true,
      mask_all_element_attributes: true,
      disable_session_recording: true,
      session_recording: { maskAllInputs: true, maskTextSelector: "*" },
    });
    expect(posthog.identify).toHaveBeenCalledWith("3f1c0f9e-0000-4000-8000-000000000001");
    expect(posthog.identify.mock.calls[0]).toHaveLength(1);
    expect(posthog.startSessionRecording).not.toHaveBeenCalled();

    state.roles = ["admin"];
    render(<AnalyticsTracker config={{ key: "k", env: "production" }} />);
    await vi.waitFor(() => expect(posthog.startSessionRecording).toHaveBeenCalled());
  });
});
