#!/usr/bin/env python3
"""
Master script: run every data script in scripts/ for every ticker listed in stocks.txt.

Discovers tickers from stocks.txt (one per line, optional $ prefix), runs get_news,
get_financials, get_filings, get_insider, get_prices, get_estimates, get_peers for
each, writes output into stocks/[TICKER]/, and writes a run summary to reports/.

Optionally, can generate per-ticker LLM reports (report.json/report.md) and a
portfolio rollup report after the data refresh.

Usage (from repo root):
  python backend/run.py
  python backend/run.py --tickers AAPL,MSFT,GOOGL
  python backend/run.py --dry-run
  python backend/run.py --no-generate-reports
  python backend/run.py --no-generate-portfolio-report
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
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
    """Resolve repository root (parent of backend/)."""
    return Path(__file__).resolve().parent.parent


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

# ANSI helpers — disabled automatically when stdout is not a TTY
_TTY = sys.stdout.isatty()
_R  = "\033[0m"   # reset
_B  = "\033[1m"   # bold
_D  = "\033[2m"   # dim
_G  = "\033[32m"  # green
_Y  = "\033[33m"  # yellow
_C  = "\033[36m"  # cyan
_GR = "\033[90m"  # gray

_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class ProgressSpinner:
    """Braille spinner + coloured progress bar, animated in a background thread."""

    def __init__(self, total: int) -> None:
        self._total = total
        self._step = 0
        self._ticker = ""
        self._script = ""
        self._idx = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def update(self, step: int, ticker: str, script: str) -> None:
        with self._lock:
            self._step = step
            self._ticker = ticker
            self._script = script

    def _render(self) -> str:
        with self._lock:
            step, total = self._step, self._total
            ticker, script = self._ticker, self._script

        frame = _FRAMES[self._idx % len(_FRAMES)]
        self._idx += 1
        width = 22
        filled = int(width * step / total) if total else width
        pct = int(100 * step / total) if total else 100

        if _TTY:
            bar = f"{_G}{'█' * filled}{_GR}{'░' * (width - filled)}{_R}"
            return (
                f"{_C}{frame}{_R} "
                f"[{bar}] "
                f"{_B}{step}/{total}{_R} "
                f"{_D}({pct:3d}%){_R}  "
                f"{_B}{_Y}{ticker}{_R} "
                f"{_D}› {script}{_R}"
            )
        else:
            bar_plain = "=" * filled + (">" if filled < width else "") + " " * max(0, width - filled - 1)
            return f"[{bar_plain}] {step}/{total} ({pct:3d}%)  {ticker} | {script}"

    def _loop(self) -> None:
        while not self._stop.is_set():
            if _TTY:
                sys.stdout.write(f"\r\033[2K{self._render()}")
            else:
                sys.stdout.write(f"\r{self._render():<110}")
            sys.stdout.flush()
            self._stop.wait(0.08)

    def stop(self, failed: int = 0) -> None:
        self._stop.set()
        self._thread.join()
        total = self._total
        full_bar = f"{_G}{'█' * 22}{_R}" if _TTY else "=" * 22
        if failed:
            icon = f"{_Y}✖{_R}" if _TTY else "x"
            note = f"{_B}Done — {failed} failure(s){_R}" if _TTY else f"Done — {failed} failure(s)"
        else:
            icon = f"{_G}✔{_R}" if _TTY else "v"
            note = f"{_G}{_B}All done!{_R}" if _TTY else "All done!"
        if _TTY:
            sys.stdout.write(f"\r\033[2K{icon} [{full_bar}] {_B}{total}/{total}{_R} (100%)   {note}\n")
        else:
            sys.stdout.write(f"\r{icon} [{full_bar}] {_B}{total}/{total}{_R} (100%)   {note}\n")
        sys.stdout.flush()


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
        help="Comma-separated tickers (default: read from stocks.txt)",
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
    ap.add_argument(
        "--generate-reports",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="After data refresh, generate stocks/<TICKER>/report.json and report.md (default: enabled; requires LLM API key)",
    )
    ap.add_argument(
        "--generate-portfolio-report",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="After all tickers, generate reports/portfolio_report_YYYY-MM-DD.md (default: enabled; requires per-ticker reports)",
    )
    ap.add_argument(
        "--provider",
        default="either",
        choices=("either", "openai", "anthropic"),
        help="LLM provider for report generation (default: either)",
    )
    ap.add_argument(
        "--model",
        default=None,
        help="Override LLM model name for report generation",
    )
    ap.add_argument(
        "--skip-filing-fetch",
        action="store_true",
        help="When generating reports, do not fetch/cache latest 10-K/10-Q (uses cached filing if present)",
    )
    ap.add_argument(
        "--refresh-filing",
        action="store_true",
        help="When generating reports, force re-fetch of latest 10-K/10-Q even if cached",
    )
    args = ap.parse_args()

    root = repo_root()
    scripts_dir = root / "backend" / "scripts"
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

    scripts_list = [s[0] for s in SCRIPT_SPECS]
    if args.generate_reports:
        scripts_list.append("generate_report.py")
    if args.generate_portfolio_report:
        scripts_list.append("generate_portfolio_report.py")

    steps_per_ticker = len(SCRIPT_SPECS) + (1 if args.generate_reports else 0)
    total_steps = (len(tickers) * steps_per_ticker) + (1 if args.generate_portfolio_report else 0)
    log_lines = [
        f"# Data run summary" + (" (dry run)" if args.dry_run else ""),
        f"**Started:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Tickers:** {', '.join(tickers)}",
        f"**Scripts:** {', '.join(scripts_list)}",
        "",
        "| Ticker | Script | Status |",
        "|--------|--------|--------|",
    ]
    failed = []
    step = 0
    spinner = ProgressSpinner(total_steps)

    for ticker in tickers:
        ticker_dir = stocks_dir / ticker
        if not args.dry_run:
            ticker_dir.mkdir(parents=True, exist_ok=True)

        for script_name, extra_args in SCRIPT_SPECS:
            step += 1
            spinner.update(step, ticker, script_name)
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

        # Optional: generate per-ticker report after data refresh.
        if args.generate_reports:
            step += 1
            spinner.update(step, ticker, "generate_report.py")
            if args.dry_run:
                log_lines.append(f"| {ticker} | generate_report.py | ok |")
            else:
                cmd = [
                    sys.executable,
                    str(scripts_dir / "generate_report.py"),
                    ticker,
                    "--provider",
                    args.provider,
                ]
                if args.model:
                    cmd.extend(["--model", args.model])
                if args.skip_filing_fetch:
                    cmd.append("--skip-filing-fetch")
                if args.refresh_filing:
                    cmd.append("--refresh-filing")
                result = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=240)
                ok = result.returncode == 0
                status = "ok" if ok else "FAIL"
                if not ok:
                    stderr = (result.stderr or "").strip()[:500]
                    failed.append((ticker, "generate_report.py", stderr or result.stdout or "no output"))
                log_lines.append(f"| {ticker} | generate_report.py | {status} |")

    # Optional: portfolio rollup report (one-time).
    if args.generate_portfolio_report:
        step += 1
        spinner.update(step, "PORTFOLIO", "generate_portfolio_report.py")
        if args.dry_run:
            log_lines.append(f"| PORTFOLIO | generate_portfolio_report.py | ok |")
        else:
            cmd = [
                sys.executable,
                str(scripts_dir / "generate_portfolio_report.py"),
                "--provider",
                args.provider,
            ]
            if args.model:
                cmd.extend(["--model", args.model])
            # If we didn't generate per-ticker reports in this run, allow rollup to regenerate them.
            if not args.generate_reports:
                cmd.append("--regenerate-missing")
            result = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=600)
            ok = result.returncode == 0
            status = "ok" if ok else "FAIL"
            if not ok:
                stderr = (result.stderr or "").strip()[:500]
                failed.append(("PORTFOLIO", "generate_portfolio_report.py", stderr or result.stdout or "no output"))
            log_lines.append(f"| PORTFOLIO | generate_portfolio_report.py | {status} |")

    spinner.stop(failed=len(failed))
    elapsed = time.perf_counter() - start
    log_lines.extend(
        [
            "",
            f"**Elapsed:** {elapsed:.1f}s",
            f"**Finished:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]
    )
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
        extra = " + portfolio report" if args.generate_portfolio_report else ""
        extra = extra + " + per-ticker reports" if args.generate_reports else extra
        print(f"Dry run: would process {len(tickers)} tickers with {len(SCRIPT_SPECS)} scripts each{extra}.")


if __name__ == "__main__":
    main()
