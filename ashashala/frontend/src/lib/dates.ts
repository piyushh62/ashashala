import { format, parseISO, isValid } from "date-fns";

/** Today as an ISO date string (yyyy-MM-dd) for <input type="date"> defaults. */
export function todayIso(): string {
  return format(new Date(), "yyyy-MM-dd");
}

/**
 * Format an ISO date/datetime string for display (e.g. "14 Jul 2026").
 * Returns the raw input unchanged if it isn't a parseable date, so callers can
 * safely pass server values without guarding.
 */
export function formatDate(iso: string | null | undefined, pattern = "d MMM yyyy"): string {
  if (!iso) return "—";
  const parsed = parseISO(iso);
  return isValid(parsed) ? format(parsed, pattern) : iso;
}

/** Format an ISO datetime with time (e.g. "14 Jul 2026, 3:04 PM"). */
export function formatDateTime(iso: string | null | undefined): string {
  return formatDate(iso, "d MMM yyyy, h:mm a");
}
