import type { ReportFields } from "./schema";

function isoDateUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

export function renderReportMarkdown(ticker: string, report: ReportFields, asOfUtc?: string | null): string {
  const t = ticker.trim().toUpperCase();
  const dateStr = (asOfUtc && asOfUtc.trim()) || isoDateUtc();

  const moat = report.moat ?? "unknown";
  const fin = report.financial_health ?? "unknown";
  const val = report.valuation ?? "unknown";

  const base = (report.base_case ?? "").trim();
  const up = (report.upside_case ?? "").trim();
  const down = (report.downside_case ?? "").trim();

  const action = (report.action ?? "").trim();
  const reasoning = (report.reasoning ?? "").trim();

  // Keep headings aligned with backend template (including emojis).
  return (
    `# Analysis: ${t} - ${dateStr}\n\n` +
    "## 🎯 Thesis Alignment\n" +
    `- [ ] Moat: ${moat}\n` +
    `- [ ] Financial Health: ${fin}\n` +
    `- [ ] Valuation: ${val}\n\n` +
    '## 📊 The "Three Cases"\n' +
    `1. **Base Case**: ${base}\n` +
    `2. **Upside**: ${up}\n` +
    `3. **Downside**: ${down}\n\n` +
    "## ⚖️ Final Decision\n" +
    `**Action:** ${action}\n` +
    `**Reasoning:** ${reasoning}\n`
  );
}

