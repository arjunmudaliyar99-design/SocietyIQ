import { describe, expect, it } from "vitest";

import { phoneToE164, validateInvite } from "./invite-form";

const base = { name: "", email: "", phone: "", role: "committee" as const };

describe("invite form", () => {
  it("needs an email or a phone number", () => {
    expect(validateInvite(base)).toBe("setup.needContact");
    expect(validateInvite({ ...base, email: "a@example.com" })).toBeNull();
    expect(validateInvite({ ...base, phone: "98000 00000" })).toBeNull();
  });

  it("checks email and phone shape", () => {
    expect(validateInvite({ ...base, email: "not-an-email" })).toBe("setup.invalidEmail");
    expect(validateInvite({ ...base, phone: "12345" })).toBe("setup.invalidPhone");
    expect(validateInvite({ ...base, phone: "+91 98000 00000" })).toBeNull();
  });

  it("stores phones as E.164", () => {
    expect(phoneToE164("98000 00000")).toBe("+919800000000");
    expect(phoneToE164("+91 98000 00000")).toBe("+919800000000");
  });
});
