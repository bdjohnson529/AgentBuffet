from __future__ import annotations

import os
from pathlib import Path


def load_repo_env(repo_root: Path, *, override: bool = False) -> bool:
    """
    Load secrets from a repo-root `.env` file into environment variables.

    Returns True if a `.env` file existed and was processed.

    Tries python-dotenv when available; falls back to a tiny parser so
    `.env` works even if dependencies aren't installed yet.
    """
    env_path = repo_root / ".env"
    if not env_path.exists():
        return False

    # Prefer python-dotenv when present.
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path, override=override)
        return True
    except Exception:
        pass

    # Minimal parser: KEY=VALUE, supports single/double quotes, ignores comments/blank lines.
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        if not key:
            continue
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        if not override and key in os.environ:
            continue
        os.environ[key] = val

    return True

