from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Optional

import requests

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore


def _sec_headers() -> dict[str, str]:
    # Allow override via .env / environment.
    ua = os.getenv("SEC_USER_AGENT") or "InvestmentAnalysis/1.0 (research; contact@example.com)"
    return {"User-Agent": ua}


@dataclass(frozen=True)
class LatestFilingResult:
    ok: bool
    status: str
    meta_path: Path
    html_path: Path
    txt_path: Path
    meta: dict[str, Any]


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _select_latest_10k_or_10q(filings: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    # filings.json is generally newest-first already; still, be defensive:
    def key(f: dict[str, Any]) -> str:
        return str(f.get("filingDate") or "")

    sorted_filings = sorted(filings, key=key, reverse=True)
    for f in sorted_filings:
        form = (f.get("form") or "").upper().strip()
        if form in {"10-K", "10-Q"} and (f.get("documentUrl") or ""):
            return f
    return None


def _html_to_text(html: str) -> str:
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required to parse SEC HTML filings")

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")

    # Normalize whitespace / blank lines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _keyword_snippets(text: str, keywords: list[str], window: int = 450, limit: int = 12) -> list[dict[str, Any]]:
    """
    Extract small, auditable snippets around keywords for later LLM use/citation.
    This is intentionally simple and deterministic.
    """
    out: list[dict[str, Any]] = []
    lower = text.lower()
    for kw in keywords:
        k = kw.lower()
        start = 0
        while len(out) < limit:
            idx = lower.find(k, start)
            if idx == -1:
                break
            a = max(0, idx - window)
            b = min(len(text), idx + len(kw) + window)
            snippet = text[a:b].strip()
            out.append({"keyword": kw, "start": a, "end": b, "snippet": snippet})
            start = idx + len(k)
        if len(out) >= limit:
            break
    return out


def fetch_and_cache_latest_filing(
    ticker: str,
    stocks_dir: Path,
    *,
    refresh: bool = False,
    polite_delay_sec: float = 0.2,
) -> LatestFilingResult:
    """
    Fetch the latest 10-K/10-Q filing HTML referenced by stocks/<TICKER>/filings.json,
    cache raw HTML and cleaned text, and write a meta JSON.

    Files written:
      - stocks/<TICKER>/filing_latest.html
      - stocks/<TICKER>/filing_latest.txt
      - stocks/<TICKER>/filing_latest.meta.json
    """
    t = ticker.strip().upper()
    tdir = stocks_dir / t
    tdir.mkdir(parents=True, exist_ok=True)

    meta_path = tdir / "filing_latest.meta.json"
    html_path = tdir / "filing_latest.html"
    txt_path = tdir / "filing_latest.txt"

    filings_obj = _read_json(tdir / "filings.json") or {}
    filings = filings_obj.get("filings") if isinstance(filings_obj, dict) else None
    if not isinstance(filings, list):
        meta = {"ticker": t, "status": "no_filings_json", "updatedAtUtc": datetime.now(timezone.utc).isoformat()}
        _write_json(meta_path, meta)
        return LatestFilingResult(False, "no_filings_json", meta_path, html_path, txt_path, meta)

    target = _select_latest_10k_or_10q([x for x in filings if isinstance(x, dict)])
    if not target:
        meta = {"ticker": t, "status": "no_10k_10q_found", "updatedAtUtc": datetime.now(timezone.utc).isoformat()}
        _write_json(meta_path, meta)
        return LatestFilingResult(False, "no_10k_10q_found", meta_path, html_path, txt_path, meta)

    url = str(target.get("documentUrl") or "")
    form = str(target.get("form") or "")
    filing_date = str(target.get("filingDate") or "")
    accession = str(target.get("accessionNumber") or "")

    prev_meta = _read_json(meta_path) if meta_path.exists() else None
    if not refresh and prev_meta and prev_meta.get("documentUrl") == url and html_path.exists() and txt_path.exists():
        prev_meta2 = dict(prev_meta)
        prev_meta2["status"] = "cached"
        prev_meta2["updatedAtUtc"] = datetime.now(timezone.utc).isoformat()
        _write_json(meta_path, prev_meta2)
        return LatestFilingResult(True, "cached", meta_path, html_path, txt_path, prev_meta2)

    # SEC politeness
    time.sleep(polite_delay_sec)

    try:
        resp = requests.get(url, headers=_sec_headers(), timeout=30)
        resp.raise_for_status()
    except Exception as e:
        meta = {
            "ticker": t,
            "status": "fetch_failed",
            "error": str(e),
            "form": form,
            "filingDate": filing_date,
            "accessionNumber": accession,
            "documentUrl": url,
            "updatedAtUtc": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(meta_path, meta)
        return LatestFilingResult(False, "fetch_failed", meta_path, html_path, txt_path, meta)

    html_bytes = resp.content or b""
    html_hash = _sha256_bytes(html_bytes)
    html_text = html_bytes.decode(resp.encoding or "utf-8", errors="replace")
    html_path.write_text(html_text, encoding="utf-8")

    try:
        cleaned = _html_to_text(html_text)
    except Exception as e:
        meta = {
            "ticker": t,
            "status": "parse_failed",
            "error": str(e),
            "form": form,
            "filingDate": filing_date,
            "accessionNumber": accession,
            "documentUrl": url,
            "htmlSha256": html_hash,
            "updatedAtUtc": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(meta_path, meta)
        return LatestFilingResult(False, "parse_failed", meta_path, html_path, txt_path, meta)

    txt_path.write_text(cleaned + "\n", encoding="utf-8")
    txt_hash = _sha256_bytes(cleaned.encode("utf-8"))

    snippets = _keyword_snippets(
        cleaned,
        keywords=[
            "Item 2.",
            "Management's Discussion",
            "Results of Operations",
            "Liquidity",
            "Capital Resources",
            "Risk Factors",
            "Outlook",
            "guidance",
            "revenue",
            "gross margin",
            "cash",
            "debt",
        ],
    )

    meta = {
        "ticker": t,
        "status": "ok",
        "form": form,
        "filingDate": filing_date,
        "accessionNumber": accession,
        "documentUrl": url,
        "fetchedAtUtc": datetime.now(timezone.utc).isoformat(),
        "htmlSha256": html_hash,
        "textSha256": txt_hash,
        "snippets": snippets,
    }
    _write_json(meta_path, meta)
    return LatestFilingResult(True, "ok", meta_path, html_path, txt_path, meta)

