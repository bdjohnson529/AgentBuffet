#!/usr/bin/env python3
"""
Fetch comparable/peer tickers for a company.

Uses yfinance (no API key). Returns list of peer tickers and optional names
for use in comparison or running other scripts (e.g. get_financials) on peers.

Usage:
  python get_peers.py AAPL
  python get_peers.py AAPL --format markdown -o stocks/AAPL/peers.json
"""

import argparse
import json
import sys
from typing import Any, List, Optional

try:
    import yfinance as yf
except ImportError:
    print("Install: pip install yfinance", file=sys.stderr)
    sys.exit(1)


def get_peers(ticker: str) -> dict:
    """Return list of peer/comparable tickers from yfinance."""
    ticker = ticker.upper().strip()
    t = yf.Ticker(ticker)
    info = t.info

    # yfinance may expose recommendedSymbols, similarCompanies, or sector peers
    peers_raw = info.get("recommendedSymbols") or info.get("similarCompanies") or info.get("peerSymbols") or []
    if isinstance(peers_raw, str):
        peers_raw = [s.strip() for s in peers_raw.split(",") if s.strip()]

    peers = []
    for p in (peers_raw or [])[:30]:
        if isinstance(p, dict):
            sym = (p.get("symbol") or p.get("ticker") or p.get("Symbol")).strip().upper()
            name = p.get("shortName") or p.get("longName") or p.get("name") or sym
            if sym:
                peers.append({"ticker": sym, "name": name})
        elif isinstance(p, str) and p.strip():
            peers.append({"ticker": p.strip().upper(), "name": p.strip()})

    # Dedupe by ticker
    seen = set()
    unique = []
    for x in peers:
        if x["ticker"] not in seen and x["ticker"] != ticker:
            seen.add(x["ticker"])
            unique.append(x)

    return {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "count": len(unique),
        "peers": unique,
    }


def to_markdown(data: dict) -> str:
    lines = [f"# Peers: {data.get('name', '')} ({data.get('ticker', '')})\n\n"]
    lines.append("Sector: {}  \nIndustry: {}\n\n".format(data.get("sector") or "N/A", data.get("industry") or "N/A"))
    lines.append("| Ticker | Name |\n|--------|------|\n")
    for p in data.get("peers", []):
        lines.append("| {} | {} |\n".format(p.get("ticker", ""), (p.get("name") or "").replace("|", "\\|")))
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Get peer/comparable tickers (yfinance).")
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument("-f", "--format", choices=("json", "markdown"), default="json", help="Output format")
    ap.add_argument("-o", "--out", help="Write output to this file (default: stdout)")
    args = ap.parse_args()

    try:
        data = get_peers(args.ticker)
    except Exception as e:
        print(json.dumps({"error": str(e), "ticker": args.ticker}), file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        text = json.dumps(data, indent=2)
    else:
        text = to_markdown(data)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
