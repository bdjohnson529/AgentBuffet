from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class FactsBundle:
    ticker: str
    as_of_utc: str
    facts: dict[str, Any]
    missing: list[str]


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _pick(d: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in keys:
        if k in d and d[k] is not None:
            out[k] = d[k]
    return out


def load_facts_for_ticker(ticker: str, stocks_dir: Path) -> FactsBundle:
    """
    Deterministically load and normalize facts from stocks/<TICKER>/ artifacts.
    This layer should not make judgments; it just extracts and compresses inputs.
    """
    t = ticker.strip().upper()
    tdir = stocks_dir / t

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    missing: list[str] = []

    def read_or_missing(name: str) -> Optional[dict[str, Any]]:
        p = tdir / name
        obj = _read_json(p)
        if obj is None:
            missing.append(name)
        return obj

    financials = read_or_missing("financials.json") or {}
    prices = read_or_missing("prices.json") or {}
    news = read_or_missing("news.json") or {}
    filings = read_or_missing("filings.json") or {}
    insider = read_or_missing("insider.json") or {}
    estimates = read_or_missing("estimates.json") or {}
    peers = read_or_missing("peers.json") or {}

    facts: dict[str, Any] = {
        "ticker": t,
        "company": _pick(financials, ["name", "sector", "industry", "currency"]),
        "financials": _pick(
            financials,
            [
                "marketCap",
                "enterpriseValue",
                "trailingPE",
                "forwardPE",
                "pegRatio",
                "priceToBook",
                "priceToSales",
                "revenue",
                "revenueGrowth",
                "grossMargins",
                "operatingMargins",
                "profitMargins",
                "operatingCashFlow",
                "freeCashFlow",
                "totalDebt",
                "totalCash",
                "debtToEquity",
                "currentRatio",
                "quickRatio",
                "roe",
                "roa",
                "earningsGrowth",
                "dividendYield",
                "beta",
                "52WeekHigh",
                "52WeekLow",
            ],
        ),
        "prices": prices.get("summary") if isinstance(prices.get("summary"), dict) else {},
        "news": (news.get("items") or [])[:8] if isinstance(news.get("items"), list) else [],
        "filings": (filings.get("filings") or [])[:10] if isinstance(filings.get("filings"), list) else [],
        "insider": (insider.get("filings") or [])[:10] if isinstance(insider.get("filings"), list) else [],
        "estimates": _pick(
            estimates,
            [
                "targetMeanPrice",
                "targetHighPrice",
                "targetLowPrice",
                "recommendationKey",
                "recommendationMean",
                "numberOfAnalystOpinions",
                "nextEarningsDate",
            ],
        )
        if isinstance(estimates, dict)
        else {},
        "peers": peers.get("peers") if isinstance(peers.get("peers"), list) else [],
    }

    # Filing cache placeholders (added by filings crawler if present)
    meta_path = tdir / "filing_latest.meta.json"
    txt_path = tdir / "filing_latest.txt"
    meta = _read_json(meta_path) if meta_path.exists() else None
    filing_text = None
    try:
        if txt_path.exists():
            filing_text = txt_path.read_text(encoding="utf-8")
    except Exception:
        filing_text = None
    if meta or filing_text:
        facts["latest_filing"] = {
            "meta": meta or {},
            # Keep the full text out of the core bundle by default; callers can add excerpts/snippets.
            "has_text": bool(filing_text),
        }

    return FactsBundle(ticker=t, as_of_utc=as_of, facts=facts, missing=missing)

