#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


_ROOT = repo_root()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.intelligence.env import load_repo_env  # noqa: E402

load_repo_env(_ROOT)


def load_tickers_from_file(stocks_file: Path) -> list[str]:
    if not stocks_file.is_file():
        return []
    raw = stocks_file.read_text(encoding="utf-8").strip()
    tickers = []
    for line in raw.splitlines():
        sym = line.strip().lstrip("$").strip().upper()
        if sym and sym.isalpha():
            tickers.append(sym)
    return sorted(set(tickers))


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a portfolio rollup report from per-ticker report.json files.")
    ap.add_argument(
        "--tickers",
        default=None,
        help="Comma-separated tickers (default: read from stocks.txt)",
    )
    ap.add_argument(
        "--provider",
        default="either",
        choices=("either", "openai", "anthropic"),
        help="Provider to use if generating missing per-ticker reports (default: either)",
    )
    ap.add_argument("--model", default=None, help="Override model for per-ticker generation")
    ap.add_argument(
        "--regenerate-missing",
        action="store_true",
        help="Generate per-ticker reports when report.json is missing",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Output path (default: reports/portfolio_report_YYYY-MM-DD.md)",
    )
    args = ap.parse_args()

    root = repo_root()
    stocks_dir = root / "stocks"
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = load_tickers_from_file(root / "stocks.txt")
        if not tickers:
            print("No tickers found. Provide --tickers or add to stocks.txt", file=sys.stderr)
            sys.exit(1)

    rows: list[dict[str, Any]] = []
    for t in tickers:
        tdir = stocks_dir / t
        rpt_path = tdir / "report.json"
        if not rpt_path.exists() and args.regenerate_missing:
            cmd = [
                sys.executable,
                str((root / "backend" / "scripts" / "generate_report.py")),
                t,
                "--provider",
                args.provider,
            ]
            if args.model:
                cmd.extend(["--model", args.model])
            p = subprocess.run(cmd, cwd=str(root))
            if p.returncode != 0:
                print(f"Failed to generate report for {t}", file=sys.stderr)

        obj = _read_json(rpt_path)
        if not obj:
            rows.append({"ticker": t, "status": "missing_report"})
            continue

        r = obj.get("report") if isinstance(obj.get("report"), dict) else {}
        rows.append(
            {
                "ticker": t,
                "action": r.get("action", ""),
                "moat": r.get("moat", ""),
                "financial_health": r.get("financial_health", ""),
                "valuation": r.get("valuation", ""),
                "reasoning": r.get("reasoning", ""),
            }
        )

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = Path(args.out) if args.out else (reports_dir / f"portfolio_report_{date_str}.md")

    buys = [x for x in rows if x.get("action") == "BUY"]
    avoids = [x for x in rows if x.get("action") in {"SELL", "AVOID"}]

    lines: list[str] = []
    lines.append(f"# Portfolio report - {date_str}\n\n")
    lines.append(f"Tickers: {', '.join(tickers)}\n\n")
    lines.append("## Summary\n")
    if buys:
        lines.append(f"- **Top BUY candidates:** {', '.join(x['ticker'] for x in buys)}\n")
    if avoids:
        lines.append(f"- **Top SELL/AVOID:** {', '.join(x['ticker'] for x in avoids)}\n")
    if not buys and not avoids:
        lines.append("- No strong BUY/SELL signals (or reports missing).\n")
    lines.append("\n## Per-ticker\n")
    for x in rows:
        t = x["ticker"]
        if x.get("status") == "missing_report":
            lines.append(f"### {t}\n- **Status:** missing `stocks/{t}/report.json`\n\n")
            continue
        lines.append(f"### {t}\n")
        lines.append(f"- **Action:** {x.get('action','')}\n")
        lines.append(f"- **Moat:** {x.get('moat','')}\n")
        lines.append(f"- **Financial Health:** {x.get('financial_health','')}\n")
        lines.append(f"- **Valuation:** {x.get('valuation','')}\n")
        if x.get("reasoning"):
            lines.append(f"- **Reasoning:** {x['reasoning']}\n")
        lines.append("\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

