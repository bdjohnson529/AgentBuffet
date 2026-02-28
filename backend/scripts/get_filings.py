#!/usr/bin/env python3
"""
Fetch SEC filings list (10-K, 10-Q, 8-K, etc.) for a company by ticker.

Uses SEC EDGAR (free, no API key). Optionally download filing document text.
Respect SEC fair use: max 10 requests/second, identify with User-Agent.

Usage:
  python get_filings.py AAPL
  python get_filings.py AAPL --forms 10-K,10-Q,8-K --limit 20
  python get_filings.py AAPL -o stocks/AAPL/filings.json
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Any, List, Optional

try:
    import requests
except ImportError:
    print("Install: pip install requests", file=sys.stderr)
    sys.exit(1)

SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT") or "InvestmentAnalysis/1.0 (research; contact@example.com)",
    "Accept": "application/json",
}
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def get_cik(ticker: str) -> Optional[str]:
    """Resolve ticker to 10-digit CIK via SEC company tickers JSON."""
    ticker = ticker.upper().strip()
    try:
        r = requests.get(COMPANY_TICKERS_URL, headers=SEC_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(json.dumps({"error": str(e), "message": "Failed to fetch company tickers"}), file=sys.stderr)
        return None
    for _, company in data.items():
        if (company.get("ticker") or "").upper() == ticker:
            cik = company.get("cik_str") or company.get("cik")
            if cik is not None:
                return str(cik).zfill(10)
    return None


def fetch_submissions(cik: str) -> Optional[dict]:
    """Fetch submissions JSON for a CIK."""
    url = SUBMISSIONS_URL.format(cik=cik)
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return None


def _recent_filings_list(submissions: dict, forms: Optional[List[str]] = None, limit: int = 50) -> List[dict]:
    """Build list of recent filings from submissions JSON (columnar or list format)."""
    filings = submissions.get("filings") or submissions
    recent = filings.get("recent")
    if not recent:
        return []

    # Columnar: {"accessionNumber": [...], "form": [...], "filingDate": [...], ...}
    if isinstance(recent, dict) and recent.get("accessionNumber") is not None:
        acc = recent["accessionNumber"]
        n = len(acc) if isinstance(acc, list) else 0
        if n == 0:
            return []
        forms_set = {f.upper().strip() for f in (forms or [])}
        out = []
        for i in range(n):
            form = (recent.get("form") or [None])[i] if i < len(recent.get("form") or []) else None
            if forms and form and form.upper() not in forms_set:
                continue
            acc_num = (recent["accessionNumber"] or [""])[i]
            acc_no_dashes = (acc_num or "").replace("-", "")
            primary = (recent.get("primaryDocument") or [""])[i] if i < len(recent.get("primaryDocument") or []) else ""
            cik = submissions.get("cik") or ""
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{primary}" if primary else ""
            out.append({
                "form": form,
                "filingDate": (recent.get("filingDate") or [""])[i] if i < len(recent.get("filingDate") or []) else "",
                "accessionNumber": acc_num,
                "primaryDocument": primary,
                "documentUrl": doc_url,
                "description": (recent.get("primaryDocDescription") or [""])[i] if i < len(recent.get("primaryDocDescription") or []) else "",
            })
            if len(out) >= limit:
                break
        return out

    # List of objects
    if isinstance(recent, list):
        forms_set = {f.upper().strip() for f in (forms or [])}
        out = []
        for f in recent[: limit * 2]:  # allow filtering
            form = (f.get("form") or "").upper()
            if forms and form not in forms_set:
                continue
            acc = (f.get("accessionNumber") or "").replace("-", "")
            cik = submissions.get("cik") or ""
            primary = f.get("primaryDocument") or ""
            out.append({
                "form": f.get("form"),
                "filingDate": f.get("filingDate"),
                "accessionNumber": f.get("accessionNumber"),
                "primaryDocument": primary,
                "documentUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{primary}" if primary else "",
                "description": f.get("primaryDocDescription"),
            })
            if len(out) >= limit:
                break
        return out

    return []


def get_filings(ticker: str, forms: Optional[list[str]] = None, limit: int = 50) -> dict:
    """Return SEC filings list for the given ticker."""
    cik = get_cik(ticker)
    if not cik:
        return {"ticker": ticker.upper(), "error": "CIK not found", "filings": []}
    time.sleep(0.2)  # be nice to SEC
    submissions = fetch_submissions(cik)
    if not submissions:
        return {"ticker": ticker.upper(), "cik": cik, "error": "Failed to fetch submissions", "filings": []}

    name = submissions.get("name") or ticker
    recent = _recent_filings_list(submissions, forms=forms, limit=limit)
    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "name": name,
        "count": len(recent),
        "filings": recent,
    }


def main():
    ap = argparse.ArgumentParser(description="Get SEC filings for a ticker (EDGAR).")
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument("--forms", type=str, default=None, help="Comma-separated form types (e.g. 10-K,10-Q,8-K)")
    ap.add_argument("-n", "--limit", type=int, default=30, help="Max number of filings (default 30)")
    ap.add_argument("-f", "--format", choices=("json", "markdown"), default="json", help="Output format")
    ap.add_argument("-o", "--out", help="Write output to this file (default: stdout)")
    args = ap.parse_args()

    forms = [x.strip() for x in args.forms.split(",")] if args.forms else None
    data = get_filings(args.ticker, forms=forms, limit=args.limit)

    if args.format == "json":
        text = json.dumps(data, indent=2)
    else:
        lines = [f"# SEC filings: {data.get('name', '')} ({data.get('ticker', '')})\n", f"CIK: {data.get('cik', '')}\n", f"Count: {data.get('count', 0)}\n\n"]
        for f in data.get("filings", []):
            lines.append(f"- **{f.get('form', '')}** {f.get('filingDate', '')} — {f.get('primaryDocument', '')}\n")
            if f.get("documentUrl"):
                lines.append(f"  {f['documentUrl']}\n")
        text = "".join(lines)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
