#!/usr/bin/env python3
"""
Fetch financial metrics for a company by ticker.

Uses yfinance (Yahoo Finance data, no API key). Output is structured for
downstream use by Claude or research pipelines.

Usage:
  python get_financials.py AAPL
  python get_financials.py AAPL --format markdown
  python get_financials.py AAPL -o stocks/AAPL/financials.json
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
    """Convert to float; return None if not possible."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def safe_int(val: Any) -> Optional[int]:
    """Convert to int; return None if not possible."""
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def get_financials(ticker: str) -> dict:
    """
    Return key financial metrics and statements for the given ticker.
    Uses yfinance; no API key required.
    """
    ticker = ticker.upper().strip()
    t = yf.Ticker(ticker)
    info = t.info

    # Core valuation and profitability
    metrics = {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency", "USD"),
        "marketCap": safe_float(info.get("marketCap")),
        "enterpriseValue": safe_float(info.get("enterpriseValue")),
        "trailingPE": safe_float(info.get("trailingPE")),
        "forwardPE": safe_float(info.get("forwardPE")),
        "pegRatio": safe_float(info.get("pegRatio")),
        "priceToBook": safe_float(info.get("priceToBook")),
        "priceToSales": safe_float(info.get("priceToSalesTrailing12Months")),
        "revenue": safe_float(info.get("totalRevenue")),
        "revenueGrowth": safe_float(info.get("revenueGrowth")),
        "grossMargins": safe_float(info.get("grossMargins")),
        "operatingMargins": safe_float(info.get("operatingMargins")),
        "profitMargins": safe_float(info.get("profitMargins")),
        "operatingCashFlow": safe_float(info.get("operatingCashflow")),
        "freeCashFlow": safe_float(info.get("freeCashflow")),
        "totalDebt": safe_float(info.get("totalDebt")),
        "totalCash": safe_float(info.get("totalCash")),
        "debtToEquity": safe_float(info.get("debtToEquity")),
        "currentRatio": safe_float(info.get("currentRatio")),
        "quickRatio": safe_float(info.get("quickRatio")),
        "roe": safe_float(info.get("returnOnEquity")),
        "roa": safe_float(info.get("returnOnAssets")),
        "earningsGrowth": safe_float(info.get("earningsGrowth")),
        "dividendYield": safe_float(info.get("dividendYield")),
        "beta": safe_float(info.get("beta")),
        "52WeekHigh": safe_float(info.get("fiftyTwoWeekHigh")),
        "52WeekLow": safe_float(info.get("fiftyTwoWeekLow")),
    }

    # Drop None values for cleaner output (optional: keep for explicit "missing")
    metrics_clean = {k: v for k, v in metrics.items() if v is not None}

    # Latest income statement snapshot (annual)
    try:
        inc = t.income_stmt
        if inc is not None and not inc.empty:
            metrics_clean["income_stmt_columns"] = list(inc.columns.astype(str)[:4])  # recent periods
            metrics_clean["income_stmt"] = inc.iloc[:, :4].to_dict() if inc.shape[1] else None
    except Exception:
        metrics_clean["income_stmt"] = None

    # Latest balance sheet snapshot
    try:
        bal = t.balance_sheet
        if bal is not None and not bal.empty:
            metrics_clean["balance_sheet_columns"] = list(bal.columns.astype(str)[:4])
            metrics_clean["balance_sheet"] = bal.iloc[:, :4].to_dict() if bal.shape[1] else None
    except Exception:
        metrics_clean["balance_sheet"] = None

    # Cash flow snapshot
    try:
        cf = t.cashflow
        if cf is not None and not cf.empty:
            metrics_clean["cashflow_columns"] = list(cf.columns.astype(str)[:4])
            metrics_clean["cashflow"] = cf.iloc[:, :4].to_dict() if cf.shape[1] else None
    except Exception:
        metrics_clean["cashflow"] = None

    return metrics_clean


def to_markdown(data: dict) -> str:
    """Convert financials dict to a markdown string."""
    lines = [f"# Financials: {data.get('ticker', '')} — {data.get('name', '')}\n"]
    lines.append("## Key metrics\n")
    skip = {"income_stmt", "balance_sheet", "cashflow", "income_stmt_columns", "balance_sheet_columns", "cashflow_columns"}
    for k, v in data.items():
        if k in skip or v is None:
            continue
        if isinstance(v, float):
            if 0 < abs(v) < 1e-3 or abs(v) >= 1e9:
                lines.append(f"- **{k}:** {v:.4g}\n")
            else:
                lines.append(f"- **{k}:** {v:,.2f}\n")
        else:
            lines.append(f"- **{k}:** {v}\n")

    for table in ("income_stmt", "balance_sheet", "cashflow"):
        if table not in data or data[table] is None:
            continue
        lines.append(f"\n## {table.replace('_', ' ').title()}\n")
        # Simple table: rows x first few periods
        lines.append("(See JSON output for full table.)\n")
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Get financial metrics for a ticker (yfinance).")
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument("-f", "--format", choices=("json", "markdown"), default="json", help="Output format")
    ap.add_argument("-o", "--out", help="Write output to this file (default: stdout)")
    args = ap.parse_args()

    try:
        data = get_financials(args.ticker)
    except Exception as e:
        print(json.dumps({"error": str(e), "ticker": args.ticker}), file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        # Convert non-JSON-serializable types (e.g. numpy from yfinance)
        def sanitize(obj):
            if hasattr(obj, "item"):  # numpy scalar
                return obj.item()
            if isinstance(obj, (int, float)) and not isinstance(obj, bool):
                return obj
            if isinstance(obj, dict):
                return {str(k): sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(x) for x in obj]
            if hasattr(obj, "tolist"):  # numpy array
                return sanitize(obj.tolist())
            return obj

        data = sanitize(data)
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
