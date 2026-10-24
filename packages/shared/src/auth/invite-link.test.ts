import { describe, expect, it } from "vitest";

import { readInvite } from "./invite-link";

const id = "6f1c2a9e-3d4b-4c5a-9e8f-0a1b2c3d4e5f";

describe("readInvite", () => {
  it("reads the society and token from an invite link", () => {
    expect(readInvite({ pathname: `/invite/${id}`, search: "?token=abc123" })).toEqual({
      societyId: id,
      token: "abc123",
    });
  });

  it("ignores other pages and links without a token", () => {
    expect(readInvite({ pathname: "/bills", search: "?token=abc" })).toBeNull();
    expect(readInvite({ pathname: `/invite/${id}`, search: "" })).toBeNull();
    expect(readInvite({ pathname: "/invite/not-a-uuid", search: "?token=abc" })).toBeNull();
  });
});
