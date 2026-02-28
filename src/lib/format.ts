export function formatNumberCompact(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (!Number.isFinite(n)) return "—";

  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  const units: Array<[number, string]> = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [v, s] of units) {
    if (abs >= v) return `${sign}${(abs / v).toFixed(abs >= 10 * v ? 0 : 2)}${s}`;
  }
  return `${n.toFixed(abs >= 10 ? 0 : 2)}`;
}

export function formatPercent(p: number | null | undefined, decimals = 1): string {
  if (p === null || p === undefined) return "—";
  if (!Number.isFinite(p)) return "—";
  return `${(p * 100).toFixed(decimals)}%`;
}

export function formatDateISO(date: string | null | undefined): string {
  if (!date) return "—";
  // Input is already YYYY-MM-DD or RFC-ish; show a friendly date when possible.
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

