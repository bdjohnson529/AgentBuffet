from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_report_prompt(*, thesis_text: str, facts_bundle: dict[str, Any], max_filing_chars: int = 18000) -> str:
    """
    Build a prompt that forces the model to:
      - only use provided facts
      - output strict JSON matching our schema
      - keep reasoning short (2-3 sentences)
    """
    facts = dict(facts_bundle)

    # If we have cached filing text, include only a truncated excerpt.
    # IMPORTANT: do not pass the full filing text to the model (token blowup).
    latest = facts.get("latest_filing")
    if isinstance(latest, dict):
        latest_copy = dict(latest)
        full_text = latest_copy.pop("text", None)
        if isinstance(full_text, str) and full_text.strip():
            latest_copy["text_excerpt"] = full_text.strip()[:max_filing_chars]
        facts["latest_filing"] = latest_copy

    facts_json = json.dumps(facts, indent=2, ensure_ascii=False)

    return (
        "You are a senior equity analyst.\n"
        "Your job: generate a report decision using ONLY the facts provided.\n\n"
        "STRICT RULES:\n"
        "- Do not invent numbers, dates, guidance, customers, or products.\n"
        "- If data is missing, use 'unknown' and say so.\n"
        "- Output MUST be valid JSON and MUST match the required fields.\n"
        "- 'reasoning' must be 2-3 sentences maximum.\n\n"
        "THESIS (authoritative):\n"
        f"{thesis_text.strip()}\n\n"
        "FACTS (authoritative JSON):\n"
        f"{facts_json}\n\n"
        "OUTPUT JSON SCHEMA (keys required):\n"
        "{\n"
        '  "moat": "High|Medium|Low|unknown",\n'
        '  "financial_health": "Pass|Fail|unknown",\n'
        '  "valuation": "Over-valued|Under-valued|unknown",\n'
        '  "base_case": "string",\n'
        '  "upside_case": "string",\n'
        '  "downside_case": "string",\n'
        '  "action": "BUY|HOLD|SELL|AVOID",\n'
        '  "reasoning": "string",\n'
        '  "evidence": [{"claim": "string", "source": "string"}]\n'
        "}\n\n"
        "Now output JSON only. No markdown, no commentary.\n"
    )


def read_thesis(repo_root: Path) -> str:
    return (repo_root / "thesis.md").read_text(encoding="utf-8")

