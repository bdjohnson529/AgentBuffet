#!/usr/bin/env python3
"""
Fetch analyst estimates and price targets for a company by ticker.

Uses yfinance (no API key). Returns consensus, targets, and next earnings date.
Output is structured for Claude or research pipelines.

Usage:
  python get_estimates.py AAPL
  python get_estimates.py AAPL --format markdown -o stocks/AAPL/estimates.json
"""

import argparse
import json
import sys
from typing import Any, Optional

try:
    import yfinance as yf
except ImportError:
    print("Install: pip install yfinance", file=sys.stderr)
    sys.exit(1)


def safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def get_estimates(ticker: str) -> dict:
    """Return analyst estimates, price targets, and earnings dates."""
    ticker = ticker.upper().strip()
    t = yf.Ticker(ticker)
    info = t.info

    # Earnings dates (next and recent)
    try:
        earnings_dates = t.earnings_dates
        next_earnings = None
        if earnings_dates is not None and not earnings_dates.empty:
            # Index is often datetime; get next future date
            for ts in earnings_dates.index:
                if hasattr(ts, "strftime"):
                    try:
                        from datetime import datetime
                        if ts.replace(tzinfo=None) > datetime.now():
                            next_earnings = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
                            break
                    except Exception:
                        pass
    except Exception:
        next_earnings = None

    # Analyst price targets
    try:
        targets = t.analyst_price_targets
        if targets is not None and not targets.empty:
            targets_list = []
            for _, row in targets.head(10).iterrows():
                targets_list.append({
                    "firm": str(row.get("Firm", "")),
                    "target": safe_float(row.get("Target") or row.get("Price Target")),
                    "date": str(row.get("Date", ""))[:10] if getattr(row.get("Date"), "strftime", None) else str(row.get("Date", ""))[:10],
                })
            last_target = float(targets.iloc[0].get("Target") or targets.iloc[0].get("Price Target") or 0) if len(targets) else None
        else:
            targets_list = []
            last_target = safe_float(info.get("targetMeanPrice") or info.get("targetHighPrice"))
    except Exception:
        targets_list = []
        last_target = safe_float(info.get("targetMeanPrice") or info.get("targetHighPrice"))

    result = {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "nextEarningsDate": next_earnings,
        "targetMeanPrice": safe_float(info.get("targetMeanPrice")),
        "targetHighPrice": safe_float(info.get("targetHighPrice")),
        "targetLowPrice": safe_float(info.get("targetLowPrice")),
        "recommendationMean": safe_float(info.get("recommendationMean")),
        "recommendationKey": info.get("recommendationKey"),
        "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
        "earningsGrowth": safe_float(info.get("earningsGrowth")),
        "revenueGrowth": safe_float(info.get("revenueGrowth")),
        "recentPriceTargets": targets_list,
    }
    # Keep all keys; only drop None for optional fields so JSON has explicit structure
    return result


def to_markdown(data: dict) -> str:
    lines = [f"# Analyst estimates: {data.get('name', '')} ({data.get('ticker', '')})\n\n"]
    lines.append("- **Next earnings date:** {}\n".format(data.get("nextEarningsDate") or "N/A"))
    lines.append("- **Target mean price:** {}\n".format(data.get("targetMeanPrice") or "N/A"))
    lines.append("- **Target high / low:** {} / {}\n".format(data.get("targetHighPrice") or "N/A", data.get("targetLowPrice") or "N/A"))
    lines.append("- **Recommendation (mean):** {} ({})\n".format(data.get("recommendationMean") or "N/A", data.get("recommendationKey") or ""))
    lines.append("- **Number of analyst opinions:** {}\n".format(data.get("numberOfAnalystOpinions") or "N/A"))
    if data.get("recentPriceTargets"):
        lines.append("\n## Recent price targets\n\n")
        for r in data["recentPriceTargets"][:10]:
            lines.append("- {}: {} ({})\n".format(r.get("firm", ""), r.get("target", ""), r.get("date", "")))
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Get analyst estimates for a ticker (yfinance).")
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument("-f", "--format", choices=("json", "markdown"), default="json", help="Output format")
    ap.add_argument("-o", "--out", help="Write output to this file (default: stdout)")
    args = ap.parse_args()

    try:
        data = get_estimates(args.ticker)
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
