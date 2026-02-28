#!/usr/bin/env python3
"""
Master script: run every data script in scripts/ for every ticker listed in stocks.txt.

Discovers tickers from stocks.txt (one per line, optional $ prefix), runs get_news,
get_financials, get_filings, get_insider, get_prices, get_estimates, get_peers for
each, writes output into stocks/[TICKER]/, and writes a run summary to reports/.

Usage (from repo root):
  python run.py
  python run.py --tickers AAPL,MSFT,GOOGL
  python run.py --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Scripts to run, in order. Each entry: (script_name, [extra_args]).
# Extra args are appended after ticker and -o path.
SCRIPT_SPECS = [
    ("get_news.py", ["--limit", "25", "--format", "json"]),
    ("get_financials.py", ["--format", "json"]),
    ("get_filings.py", ["--forms", "10-K,10-Q,8-K", "--limit", "30", "--format", "json"]),
    ("get_insider.py", ["--limit", "15", "--format", "json"]),
    ("get_prices.py", ["--days", "365", "--format", "json"]),
    ("get_estimates.py", ["--format", "json"]),
    ("get_peers.py", ["--format", "json"]),
]

# Output filename (no path) for each script, keyed by script base name.
OUTPUT_FILES = {
    "get_news": "news.json",
    "get_financials": "financials.json",
    "get_filings": "filings.json",
    "get_insider": "insider.json",
    "get_prices": "prices.json",
    "get_estimates": "estimates.json",
    "get_peers": "peers.json",
}

# SEC scripts: throttle with a short delay after each run.
SEC_SCRIPTS = {"get_filings", "get_insider"}
SEC_DELAY_SEC = 0.3


def repo_root() -> Path:
    """Resolve repo root (parent of scripts/)."""
    root = Path(__file__).resolve().parent
    return root


def load_tickers_from_file(stocks_file: Path) -> list[str]:
    """Return sorted list of unique ticker symbols from stocks.txt (one per line, optional $ prefix)."""
    if not stocks_file.is_file():
        return []
    raw = stocks_file.read_text(encoding="utf-8").strip()
    tickers = []
    for line in raw.splitlines():
        sym = line.strip().lstrip("$").strip().upper()
        if sym and sym.isalpha():
            tickers.append(sym)
    return sorted(set(tickers))

def run_script(
    scripts_dir: Path,
    script_name: str,
    ticker: str,
    out_path: Path,
    extra_args: list[str],
    dry_run: bool,
) -> tuple[bool, str]:
    """Run one script for one ticker. Return (success, message)."""
    script_path = scripts_dir / script_name
    if not script_path.exists():
        return False, f"script not found: {script_path}"

    cmd = [
        sys.executable,
        str(script_path),
        ticker,
        "-o",
        str(out_path),
        *extra_args,
    ]
    if dry_run:
        return True, f"would run: {' '.join(cmd)}"

    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[:500]
            return False, f"exit {result.returncode}: {stderr or result.stdout or 'no output'}"
        return True, "ok"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run all data scripts for all tickers and write outputs to stocks/ and a summary to reports/."
    )
    ap.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated tickers (default: all subdirs of stocks/)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be run without executing",
    )
    ap.add_argument(
        "--skip-reports-summary",
        action="store_true",
        help="Do not write the run summary to reports/",
    )
    args = ap.parse_args()

    root = repo_root()
    scripts_dir = root / "scripts"
    stocks_dir = root / "stocks"
    reports_dir = root / "reports"
    stocks_file = root / "stocks.txt"

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = load_tickers_from_file(stocks_file)
        if not tickers:
            print("No tickers found in stocks.txt. Add one ticker per line (optional $ prefix) or pass --tickers AAPL,...", file=sys.stderr)
            sys.exit(1)

    reports_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    log_lines = [
        f"# Data run summary" + (" (dry run)" if args.dry_run else ""),
        f"**Started:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Tickers:** {', '.join(tickers)}",
        f"**Scripts:** {', '.join(s[0] for s in SCRIPT_SPECS)}",
        "",
        "| Ticker | Script | Status |",
        "|--------|--------|--------|",
    ]
    failed = []

    for ticker in tickers:
        ticker_dir = stocks_dir / ticker
        if not args.dry_run:
            ticker_dir.mkdir(parents=True, exist_ok=True)

        for script_name, extra_args in SCRIPT_SPECS:
            base = script_name.replace(".py", "")
            out_file = OUTPUT_FILES.get(base, f"{base}.json")
            out_path = ticker_dir / out_file

            ok, msg = run_script(
                scripts_dir, script_name, ticker, out_path, extra_args, args.dry_run
            )
            status = "ok" if ok else "FAIL"
            if not ok:
                failed.append((ticker, script_name, msg))
            log_lines.append(f"| {ticker} | {script_name} | {status} |")

            if base in SEC_SCRIPTS and ok and not args.dry_run:
                time.sleep(SEC_DELAY_SEC)

    elapsed = time.perf_counter() - start
    log_lines.extend([
        "",
        f"**Elapsed:** {elapsed:.1f}s",
        f"**Finished:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
    ])
    if failed:
        log_lines.append("")
        log_lines.append("## Failures")
        for ticker, script_name, msg in failed:
            log_lines.append(f"- **{ticker}** / **{script_name}**: {msg}")

    summary_path = reports_dir / f"data_run_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    if not args.skip_reports_summary:
        summary_path.write_text("\n".join(log_lines), encoding="utf-8")
        print(f"Wrote summary to {summary_path}")

    if not args.dry_run:
        print(f"Run complete: {len(tickers)} tickers, {len(SCRIPT_SPECS)} scripts each. Elapsed: {elapsed:.1f}s")
        if failed:
            print(f"Failures: {len(failed)}", file=sys.stderr)
            for ticker, script_name, msg in failed:
                print(f"  {ticker} / {script_name}: {msg}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Dry run: would process {len(tickers)} tickers with {len(SCRIPT_SPECS)} scripts each.")


if __name__ == "__main__":
    main()
