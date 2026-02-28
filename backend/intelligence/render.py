from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def render_report_markdown(ticker: str, report: dict[str, Any], as_of_utc: str | None = None) -> str:
    """
    Render Markdown matching templates/report.md structure.

    Expected report keys:
      moat: High|Medium|Low|unknown
      financial_health: Pass|Fail|unknown
      valuation: Over-valued|Under-valued|unknown
      base_case / upside_case / downside_case: strings
      action: BUY|HOLD|SELL|AVOID
      reasoning: 2-3 sentences
    """
    t = ticker.upper().strip()
    date_str = as_of_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    moat = report.get("moat", "unknown")
    fin = report.get("financial_health", "unknown")
    val = report.get("valuation", "unknown")

    base = (report.get("base_case") or "").strip()
    up = (report.get("upside_case") or "").strip()
    down = (report.get("downside_case") or "").strip()

    action = (report.get("action") or "").strip()
    reasoning = (report.get("reasoning") or "").strip()

    # Keep the headings exactly as in templates/report.md (including emojis).
    lines: list[str] = []
    lines.append(f"# Analysis: {t} - {date_str}\n\n")
    lines.append("## 🎯 Thesis Alignment\n")
    lines.append(f"- [ ] Moat: {moat}\n")
    lines.append(f"- [ ] Financial Health: {fin}\n")
    lines.append(f"- [ ] Valuation: {val}\n\n")
    lines.append('## 📊 The "Three Cases"\n')
    lines.append(f"1. **Base Case**: {base}\n")
    lines.append(f"2. **Upside**: {up}\n")
    lines.append(f"3. **Downside**: {down}\n\n")
    lines.append("## ⚖️ Final Decision\n")
    lines.append(f"**Action:** {action}\n")
    lines.append(f"**Reasoning:** {reasoning}\n")
    return "".join(lines)

