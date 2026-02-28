from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Optional

from .schema import ReportModel

ProviderName = Literal["openai", "anthropic"]


@dataclass(frozen=True)
class LLMConfig:
    provider: ProviderName
    model: str
    temperature: float = 0.2
    max_output_tokens: int = 900


class LLMError(RuntimeError):
    pass


def _detect_provider(requested: str) -> ProviderName:
    """
    requested: openai | anthropic | either
    """
    req = (requested or "either").strip().lower()
    if req in {"openai", "anthropic"}:
        return req  # type: ignore[return-value]
    if req != "either":
        raise LLMError(f"Unknown provider: {requested}")

    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    if has_openai and not has_anthropic:
        return "openai"
    if has_anthropic and not has_openai:
        return "anthropic"
    if has_openai and has_anthropic:
        # Default preference (can be overridden by CLI flag).
        return "openai"
    raise LLMError("No API key found. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY.")


def _parse_report_json(text: str) -> dict[str, Any]:
    try:
        obj = json.loads(text)
    except Exception as e:
        raise LLMError(f"Model did not return valid JSON: {e}") from e
    try:
        m = ReportModel.model_validate(obj)
    except Exception as e:
        raise LLMError(f"Model JSON failed schema validation: {e}") from e
    return m.model_dump()


def complete_report_json(prompt: str, *, provider: str = "either", model: Optional[str] = None) -> dict[str, Any]:
    prov = _detect_provider(provider)
    if prov == "openai":
        cfg = LLMConfig(provider="openai", model=model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
        return _openai_complete_json(cfg, prompt)
    else:
        cfg = LLMConfig(provider="anthropic", model=model or os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6"))
        return _anthropic_complete_json(cfg, prompt)


def _openai_complete_json(cfg: LLMConfig, prompt: str) -> dict[str, Any]:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise LLMError("Missing dependency: openai. Install backend requirements.") from e

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        resp = client.responses.create(
            model=cfg.model,
            input=prompt,
            temperature=cfg.temperature,
            max_output_tokens=cfg.max_output_tokens,
        )
    except Exception as e:
        raise LLMError(f"OpenAI request failed: {e}") from e

    # The SDK exposes a convenient output_text, but keep a fallback.
    text = getattr(resp, "output_text", None)
    if not text:
        # Try to recover from raw output structure
        try:
            parts = []
            for item in resp.output:  # type: ignore[attr-defined]
                if getattr(item, "type", "") == "message":
                    for c in item.content:
                        if getattr(c, "type", "") in {"output_text", "text"}:
                            parts.append(getattr(c, "text", ""))
            text = "\n".join(parts).strip()
        except Exception:
            text = ""
    if not text:
        raise LLMError("OpenAI returned empty text.")
    return _parse_report_json(text)


def _anthropic_complete_json(cfg: LLMConfig, prompt: str) -> dict[str, Any]:
    try:
        import anthropic  # type: ignore
    except Exception as e:
        raise LLMError("Missing dependency: anthropic. Install backend requirements.") from e

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    try:
        msg = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_output_tokens,
            temperature=cfg.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise LLMError(f"Anthropic request failed: {e}") from e

    # Concatenate all text blocks
    parts = []
    for block in getattr(msg, "content", []) or []:
        if getattr(block, "type", "") == "text":
            parts.append(getattr(block, "text", ""))
    text = "\n".join(parts).strip()
    if not text:
        raise LLMError("Anthropic returned empty text.")
    return _parse_report_json(text)

