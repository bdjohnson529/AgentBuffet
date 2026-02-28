#!/usr/bin/env python3
"""
Fetch recent insider transactions (Form 4 filings) for a company by ticker.

Uses SEC EDGAR (free, no API key). Lists Form 4 filings with dates and document links.
Respect SEC fair use: identify with User-Agent.

Usage:
  python get_insider.py AAPL
  python get_insider.py AAPL --limit 15 -o stocks/AAPL/insider.json
"""

import argparse
import json
import sys
import time
from typing import Any, List, Optional

try:
    import requests
except ImportError:
    print("Install: pip install requests", file=sys.stderr)
    sys.exit(1)

SEC_HEADERS = {
    "User-Agent": "InvestmentAnalysis/1.0 (research; contact@example.com)",
    "Accept": "application/json",
}
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def get_cik(ticker: str) -> Optional[str]:
    """Resolve ticker to 10-digit CIK."""
    ticker = ticker.upper().strip()
    try:
        r = requests.get(COMPANY_TICKERS_URL, headers=SEC_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
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


def _recent_form4_list(submissions: dict, limit: int = 30) -> List[dict]:
    """Extract Form 4 filings from submissions (columnar or list)."""
    filings = submissions.get("filings") or submissions
    recent = filings.get("recent")
    if not recent:
        return []

    out = []
    cik = submissions.get("cik") or ""

    if isinstance(recent, dict) and recent.get("accessionNumber") is not None:
        acc = recent["accessionNumber"]
        n = len(acc) if isinstance(acc, list) else 0
        forms = recent.get("form") or []
        for i in range(n):
            if i < len(forms) and (forms[i] or "").upper() != "4":
                continue
            acc_num = (recent["accessionNumber"] or [""])[i]
            acc_no_dashes = (acc_num or "").replace("-", "")
            primary = (recent.get("primaryDocument") or [""])[i] if i < len(recent.get("primaryDocument") or []) else ""
            out.append({
                "form": "4",
                "filingDate": (recent.get("filingDate") or [""])[i] if i < len(recent.get("filingDate") or []) else "",
                "accessionNumber": acc_num,
                "primaryDocument": primary,
                "documentUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{primary}" if primary else "",
            })
            if len(out) >= limit:
                break
        return out

    if isinstance(recent, list):
        for f in recent:
            if (f.get("form") or "").upper() != "4":
                continue
            acc = (f.get("accessionNumber") or "").replace("-", "")
            primary = f.get("primaryDocument") or ""
            out.append({
                "form": "4",
                "filingDate": f.get("filingDate"),
                "accessionNumber": f.get("accessionNumber"),
                "primaryDocument": primary,
                "documentUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{primary}" if primary else "",
            })
            if len(out) >= limit:
                break
        return out

    return out


def get_insider(ticker: str, limit: int = 30) -> dict:
    """Return recent Form 4 (insider transaction) filings for the ticker."""
    cik = get_cik(ticker)
    if not cik:
        return {"ticker": ticker.upper(), "error": "CIK not found", "filings": []}
    time.sleep(0.2)
    submissions = fetch_submissions(cik)
    if not submissions:
        return {"ticker": ticker.upper(), "cik": cik, "error": "Failed to fetch submissions", "filings": []}
    recent = _recent_form4_list(submissions, limit=limit)
    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "name": submissions.get("name") or ticker,
        "count": len(recent),
        "filings": recent,
    }


def main():
    ap = argparse.ArgumentParser(description="Get insider transactions (Form 4) for a ticker.")
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument("-n", "--limit", type=int, default=20, help="Max number of Form 4s (default 20)")
    ap.add_argument("-f", "--format", choices=("json", "markdown"), default="json", help="Output format")
    ap.add_argument("-o", "--out", help="Write output to this file (default: stdout)")
    args = ap.parse_args()

    data = get_insider(args.ticker, limit=args.limit)

    if args.format == "json":
        text = json.dumps(data, indent=2)
    else:
        lines = [f"# Insider transactions (Form 4): {data.get('name', '')} ({data.get('ticker', '')})\n", f"Count: {data.get('count', 0)}\n\n"]
        for f in data.get("filings", []):
            lines.append(f"- **{f.get('filingDate', '')}** — [ {f.get('primaryDocument', '')} ]( {f.get('documentUrl', '')} )\n")
        text = "".join(lines)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
