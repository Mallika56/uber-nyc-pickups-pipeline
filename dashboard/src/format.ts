// Display formatting shared by the charts.

const intFormat = new Intl.NumberFormat("en-US");
const compactFormat = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

export const fmtInt = (n: number) => intFormat.format(Math.round(n));
export const fmtCompact = (n: number) => compactFormat.format(n);

/** Parse "2014-09-13" as a local date, so it doesn't shift a day in US time zones. */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export const fmtDate = (iso: string) =>
  parseDate(iso).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });

export const fmtMonth = (iso: string) => parseDate(iso).toLocaleDateString("en-US", { month: "short" });

/** 0 -> "12 AM", 17 -> "5 PM". */
export function fmtHour(hour: number): string {
  const suffix = hour < 12 ? "AM" : "PM";
  const h = hour % 12 === 0 ? 12 : hour % 12;
  return `${h} ${suffix}`;
}

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const MONTH_NAMES: Record<number, string> = { 4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September" };
