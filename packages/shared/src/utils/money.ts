// Money arrives from the API as integer paise (CLAUDE.md §4.3). Formatting uses integer
// arithmetic only, so a display never shows a rounding artefact.

const rupeeFormat = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** 13100000 -> "₹1,31,000"; 1050 -> "₹10.50". Paise shown only when non-zero (docs/03 §6). */
export function formatPaise(paise: number): string {
  if (!Number.isSafeInteger(paise)) {
    throw new Error(`Money must be whole paise, got ${paise}`);
  }
  const abs = Math.abs(paise);
  const rupees = rupeeFormat.format(Math.trunc(abs / 100));
  const rest = abs % 100;
  const text = rest === 0 ? `₹${rupees}` : `₹${rupees}.${String(rest).padStart(2, "0")}`;
  return paise < 0 ? `-${text}` : text;
}
