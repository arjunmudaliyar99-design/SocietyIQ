/** "B-207" when the society has several wings, "301" when it has one (docs/03 §6: flat
 * numbers exactly as the society writes them). */
export function flatLabel(flat: { wing_name: string; flat_number: string }, wingCount: number): string {
  return wingCount > 1 ? `${flat.wing_name}-${flat.flat_number}` : flat.flat_number;
}

export const OCCUPANCIES = ["owner_occupied", "family_occupied", "let_out", "vacant"] as const;
export const USAGES = ["residential", "commercial"] as const;
export const MEMBER_TYPES = ["owner", "joint_owner", "tenant", "delegate"] as const;

/** Rupees typed by a person → paise, without floating point. Null when not a valid amount. */
export function rupeesToPaise(text: string): number | null {
  const clean = text.replace(/[₹,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  const [whole = "0", fraction = ""] = clean.split(".");
  const paise = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  return Number.isSafeInteger(paise) ? paise : null;
}

export function paiseToRupeesInput(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "";
  const rest = paise % 100;
  return rest === 0 ? String(paise / 100) : `${Math.trunc(paise / 100)}.${String(rest).padStart(2, "0")}`;
}
