// "25 Sep 2026" in English (docs/03 §6). Built by hand because recent ICU data prints
// "Sept" for en-GB and en-IN. Other languages use their own month names.

const EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Accepts a Date or an ISO date "2026-09-25". Calendar dates are shown as written, no timezone shift. */
export function formatDate(value: Date | string, language = "en"): string {
  const date = typeof value === "string" ? parseIsoDate(value) : value;
  if (language === "en") {
    return `${date.getDate()} ${EN_MONTHS[date.getMonth()]} ${date.getFullYear()}`;
  }
  return new Intl.DateTimeFormat(`${language}-IN`, {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function parseIsoDate(value: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) throw new Error(`Not an ISO date: ${value}`);
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}
