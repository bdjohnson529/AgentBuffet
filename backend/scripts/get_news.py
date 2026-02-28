#!/usr/bin/env python3
"""
Fetch financial news for a company by ticker.

Uses free Yahoo Finance RSS feeds (no API key). Output is structured for
downstream use by Claude or research pipelines.

Usage:
  python get_news.py AAPL
  python get_news.py AAPL --limit 20 --format json
  python get_news.py AAPL -o stocks/AAPL/news.json
"""

import argparse
import json
import sys
from urllib.parse import quote
from typing import Optional

try:
    import requests
except ImportError:
    print("Install: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    import feedparser
except ImportError:
    feedparser = None  # fallback to stdlib XML

RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline"
# Fallback: finance.yahoo.com RSS (same content, different base)
RSS_URL_ALT = "https://finance.yahoo.com/rss/headline"


def fetch_rss_requests(url: str) -> Optional[dict]:
    """Fetch and parse RSS with requests + feedparser or stdlib."""
    resp = requests.get(url, timeout=15, headers={"User-Agent": "InvestmentAnalysis/1.0"})
    resp.raise_for_status()
    text = resp.text

    if feedparser:
        return feedparser.parse(text)

    # Minimal stdlib fallback: parse as XML and extract items
    import xml.etree.ElementTree as ET
    root = ET.fromstring(text)
    ns = {}
    if root.tag.startswith("{"):
        ns["rss"] = root.tag[1 : root.tag.index("}")]
    channel = root.find("channel") or root.find(".//channel")
    if channel is None:
        return None
    items = []
    for item in channel.findall("item"):
        entry = {
            "title": (item.find("title") or item.find("link")).text or "",
            "link": (item.find("link") or item.find("title")).text or "",
            "published": (item.find("pubDate") or item.find("published")).text or "",
            "summary": (item.find("description") or item.find("summary")).text or "",
        }
        items.append(entry)
    return {"entries": items}


def get_news(ticker: str, limit: int = 30) -> list[dict]:
    """Return list of news items for the given ticker."""
    ticker = ticker.upper().strip()
    url = f"{RSS_URL}?s={quote(ticker)}"

    parsed = fetch_rss_requests(url)
    if not parsed:
        return []

    entries = getattr(parsed, "entries", parsed.get("entries", []))
    out = []
    for e in entries[:limit]:
        if hasattr(e, "title"):
            title = getattr(e, "title", "") or ""
            link = getattr(e, "link", "") or ""
            published = getattr(e, "published", "") or getattr(e, "updated", "")
            summary = getattr(e, "summary", "") or getattr(e, "description", "")
        else:
            title = e.get("title", "")
            link = e.get("link", "")
            published = e.get("published", "")
            summary = e.get("summary", e.get("description", ""))
        out.append({
            "title": title,
            "link": link,
            "published": published,
            "summary": (summary or "")[:500],
        })
    return out


def main():
    ap = argparse.ArgumentParser(description="Get financial news for a ticker (Yahoo Finance RSS).")
    ap.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    ap.add_argument("-n", "--limit", type=int, default=25, help="Max number of items (default 25)")
    ap.add_argument("-f", "--format", choices=("json", "markdown"), default="json", help="Output format")
    ap.add_argument("-o", "--out", help="Write output to this file (default: stdout)")
    args = ap.parse_args()

    try:
        items = get_news(args.ticker, limit=args.limit)
    except requests.RequestException as e:
        print(json.dumps({"error": str(e), "ticker": args.ticker}), file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        text = json.dumps({"ticker": args.ticker, "count": len(items), "items": items}, indent=2)
    else:
        lines = [f"# Financial news: {args.ticker}\n", f"Count: {len(items)}\n"]
        for i, x in enumerate(items, 1):
            lines.append(f"## {i}. {x['title']}\n")
            lines.append(f"- **Published:** {x['published']}\n")
            lines.append(f"- **Link:** {x['link']}\n")
            if x.get("summary"):
                lines.append(f"\n{x['summary']}\n\n")
        text = "\n".join(lines)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
