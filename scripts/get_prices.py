#!/usr/bin/env python3
"""
Fetch historical price data for a company by ticker.

Uses yfinance (no API key). Returns OHLCV and optional simple returns/volatility.
Output is structured for Claude or research pipelines.

Usage:
  python get_prices.py AAPL
  python get_prices.py AAPL --days 90 --format markdown
  python get_prices.py AAPL -o stocks/AAPL/prices.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Any, List, Optional

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


def get_prices(ticker: str, days: int = 365) -> dict:
    """Return historical daily prices and summary stats for the ticker."""
    ticker = ticker.upper().strip()
    t = yf.Ticker(ticker)
    end = datetime.now()
    start = end - timedelta(days=days)
    hist = t.history(start=start, end=end, auto_adjust=True)

    if hist is None or hist.empty:
        return {"ticker": ticker, "error": "No history returned", "series": [], "summary": {}}

    # Build compact series (date, open, high, low, close, volume)
    series = []
    for ts, row in hist.iterrows():
        series.append({
            "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10],
            "open": safe_float(row.get("Open")),
            "high": safe_float(row.get("High")),
            "low": safe_float(row.get("Low")),
            "close": safe_float(row.get("Close")),
            "volume": int(row.get("Volume", 0)) if row.get("Volume") is not None else None,
        })

    # Summary: first/last close, return over period, rough volatility (std of daily returns)
    closes = hist["Close"].dropna()
    if len(closes) >= 2:
        first_close = float(closes.iloc[0])
        last_close = float(closes.iloc[-1])
        total_return = (last_close - first_close) / first_close if first_close else None
        daily_returns = closes.pct_change().dropna()
        volatility = float(daily_returns.std()) if len(daily_returns) else None  # daily vol
    else:
        first_close = float(closes.iloc[0]) if len(closes) else None
        last_close = first_close
        total_return = None
        volatility = None

    def _f(x):
        return float(x) if x is not None and hasattr(x, "__float__") else x

    summary = {
        "periodDays": days,
        "firstDate": series[0]["date"] if series else None,
        "lastDate": series[-1]["date"] if series else None,
        "firstClose": _f(first_close),
        "lastClose": _f(last_close),
        "totalReturnPct": round(float(total_return) * 100, 4) if total_return is not None else None,
        "dailyVolatility": round(float(volatility), 6) if volatility is not None else None,
        "numPoints": len(series),
    }

    return {
        "ticker": ticker,
        "summary": summary,
        "series": series,
    }


def to_markdown(data: dict, max_rows: int = 30) -> str:
    """Render prices as markdown (summary + table of last N days)."""
    lines = [f"# Price history: {data.get('ticker', '')}\n"]
    s = data.get("summary", {})
    lines.append("## Summary\n")
    lines.append(f"- Period: {s.get('firstDate')} to {s.get('lastDate')} ({s.get('periodDays')} days)\n")
    lines.append(f"- First close: {s.get('firstClose')}\n")
    lines.append(f"- Last close: {s.get('lastClose')}\n")
    lines.append(f"- Total return: {s.get('totalReturnPct')}%\n")
    lines.append(f"- Daily volatility: {s.get('dailyVolatility')}\n\n")
    lines.append("## Recent days (last {})\n\n".format(max_rows))
    lines.append("| Date | Open | High | Low | Close | Volume |\n")
    lines.append("|------|------|------|-----|-------|--------|\n")
    for row in (data.get("series") or [])[-max_rows:]:
        lines.append("| {} | {} | {} | {} | {} | {} |\n".format(
            row.get("date", ""),
            row.get("open") or "",
            row.get("high") or "",
            row.get("low") or "",
            row.get("close") or "",
            row.get("volume") or "",
        ))
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Get historical prices for a ticker (yfinance).")
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument("-d", "--days", type=int, default=365, help="Number of calendar days of history (default 365)")
    ap.add_argument("-f", "--format", choices=("json", "markdown"), default="json", help="Output format")
    ap.add_argument("-o", "--out", help="Write output to this file (default: stdout)")
    args = ap.parse_args()

    try:
        data = get_prices(args.ticker, days=args.days)
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
