#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


# Ensure repo root is on sys.path so `import backend.*` works when running as a script.
_ROOT = repo_root()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.intelligence.env import load_repo_env  # noqa: E402

load_repo_env(_ROOT)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate per-ticker analysis report using local stock facts + an LLM."
    )
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument(
        "--provider",
        default="either",
        choices=("either", "openai", "anthropic"),
        help="LLM provider to use (default: either, auto-detect by env vars)",
    )
    ap.add_argument("--model", default=None, help="Override model name for the chosen provider")
    ap.add_argument(
        "--skip-filing-fetch",
        action="store_true",
        help="Do not fetch/cache latest 10-K/10-Q (uses cached filing_latest.* if present)",
    )
    ap.add_argument(
        "--refresh-filing",
        action="store_true",
        help="Force re-fetch of latest 10-K/10-Q even if cached",
    )
    ap.add_argument(
        "--debug-env",
        action="store_true",
        help="Print whether API keys are detected and exit (does not print key values)",
    )
    ap.add_argument(
        "--out-md",
        default=None,
        help="Write Markdown report to this path (default: stocks/<TICKER>/report.md)",
    )
    ap.add_argument(
        "--out-json",
        default=None,
        help="Write structured report JSON to this path (default: stocks/<TICKER>/report.json)",
    )
    args = ap.parse_args()

    root = repo_root()
    if args.debug_env:
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
        print(f"OPENAI_API_KEY set: {has_openai}")
        print(f"ANTHROPIC_API_KEY set: {has_anthropic}")
        sys.exit(0)

    # Heavy imports (requests/openai/anthropic/bs4) come after --debug-env.
    from backend.intelligence.filings import fetch_and_cache_latest_filing  # noqa: E402
    from backend.intelligence.load import load_facts_for_ticker  # noqa: E402
    from backend.intelligence.prompts import build_report_prompt, read_thesis  # noqa: E402
    from backend.intelligence.providers import LLMError, complete_report_json  # noqa: E402
    from backend.intelligence.render import render_report_markdown  # noqa: E402

    stocks_dir = root / "stocks"
    t = args.ticker.strip().upper()
    tdir = stocks_dir / t
    tdir.mkdir(parents=True, exist_ok=True)

    # 1) Deterministic filing fetch/cache
    filing_meta = None
    filing_status = None
    if not args.skip_filing_fetch:
        res = fetch_and_cache_latest_filing(t, stocks_dir, refresh=bool(args.refresh_filing))
        filing_meta = res.meta
        filing_status = res.status
    else:
        filing_status = "skipped"

    # 2) Deterministic facts bundle
    facts_bundle = load_facts_for_ticker(t, stocks_dir)

    # Attach filing text excerpt (bounded) to facts, if available
    filing_txt = tdir / "filing_latest.txt"
    if filing_txt.exists():
        try:
            facts_bundle.facts.setdefault("latest_filing", {})
            facts_bundle.facts["latest_filing"]["text"] = filing_txt.read_text(encoding="utf-8")
        except Exception:
            pass

    # 3) Prompt + LLM JSON synthesis
    thesis_text = read_thesis(root)
    prompt = build_report_prompt(thesis_text=thesis_text, facts_bundle=facts_bundle.facts)

    try:
        report_fields = complete_report_json(prompt, provider=args.provider, model=args.model)
    except LLMError as e:
        print(f"LLM error: {e}", file=sys.stderr)
        sys.exit(2)

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_json_obj = {
        "ticker": t,
        "asOfUtc": as_of,
        "provider": args.provider,
        "model": args.model,
        "inputsMissing": facts_bundle.missing,
        "filingFetchStatus": filing_status,
        "latestFilingMeta": filing_meta,
        "report": report_fields,
    }

    out_json = Path(args.out_json) if args.out_json else (tdir / "report.json")
    out_md = Path(args.out_md) if args.out_md else (tdir / "report.md")

    out_json.write_text(json.dumps(report_json_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(render_report_markdown(t, report_fields, as_of_utc=as_of), encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

