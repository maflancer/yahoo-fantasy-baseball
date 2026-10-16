/** "Mar 27" from an ISO date (YYYY-MM-DD), parsed as a local date to avoid timezone shifts. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
