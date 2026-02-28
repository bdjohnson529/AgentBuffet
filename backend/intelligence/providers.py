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


def _provider_candidates(requested: str) -> list[ProviderName]:
    """
    requested: openai | anthropic | either
    Returns providers to try, in priority order.
    """
    req = (requested or "either").strip().lower()
    if req in {"openai", "anthropic"}:
        return [req]  # type: ignore[list-item]
    if req != "either":
        raise LLMError(f"Unknown provider: {requested}")

    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    if not has_openai and not has_anthropic:
        raise LLMError("No API key found. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY.")

    # Default preference order if both are available.
    out: list[ProviderName] = []
    if has_anthropic:
        out.append("anthropic")
    if has_openai:
        out.append("openai")
    return out


def _maybe_unwrap_markdown_fences(text: str) -> str:
    """
    If the model wrapped JSON in ```json fences, unwrap the first fenced block.
    """
    s = (text or "").strip()
    if "```" not in s:
        return s
    parts = s.split("```")
    if len(parts) < 3:
        return s
    # parts[1] is language header + content; prefer it
    candidate = parts[1]
    # Remove optional leading language token on the first line.
    lines = candidate.splitlines()
    if lines and lines[0].strip().lower() in {"json", "javascript"}:
        candidate = "\n".join(lines[1:])
    return candidate.strip()


def _extract_json_object(text: str) -> Optional[str]:
    """
    Best-effort extraction of a top-level JSON object from arbitrary text.
    We intentionally keep this simple and conservative.
    """
    s = (text or "").strip()
    if not s:
        return None
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return s[start : end + 1].strip()


def _parse_report_json(text: str) -> dict[str, Any]:
    raw = text or ""
    s = _maybe_unwrap_markdown_fences(raw)
    try:
        obj = json.loads(s)
    except Exception as e:
        extracted = _extract_json_object(s)
        if extracted and extracted != s:
            try:
                obj = json.loads(extracted)
            except Exception:
                snippet = (s[:300] + "…") if len(s) > 300 else s
                raise LLMError(f"Model did not return valid JSON: {e}. Output starts with: {snippet!r}") from e
        else:
            snippet = (s[:300] + "…") if len(s) > 300 else s
            raise LLMError(f"Model did not return valid JSON: {e}. Output starts with: {snippet!r}") from e
    try:
        m = ReportModel.model_validate(obj)
    except Exception as e:
        raise LLMError(f"Model JSON failed schema validation: {e}") from e
    return m.model_dump()


def complete_report_json(prompt: str, *, provider: str = "either", model: Optional[str] = None) -> dict[str, Any]:
    last_err: Optional[Exception] = None
    for prov in _provider_candidates(provider):
        try:
            if prov == "openai":
                cfg = LLMConfig(provider="openai", model=model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
                return _openai_complete_json(cfg, prompt)
            else:
                cfg = LLMConfig(provider="anthropic", model=model or os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6"))
                return _anthropic_complete_json(cfg, prompt)
        except Exception as e:
            last_err = e
            continue
    raise LLMError(str(last_err) if last_err else "LLM request failed.")


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

