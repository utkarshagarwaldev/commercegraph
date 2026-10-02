"""Local settings. Never include the API key in results or representations."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    model: str = "gemini-3.5-flash-lite"
    mode: str = "live"
    dataset_path: str | None = None
    tls12: bool = False

    @classmethod
    def from_env(cls):
        local = dotenv_values(Path.cwd() / ".env")

        def setting(name, default=""):
            return os.environ.get(name, local.get(name) or default)

        mode = setting("APP_MODE", "live").strip().lower()
        if mode not in {"live", "offline"}:
            raise ValueError("APP_MODE must be live or offline")
        tls12 = setting("GEMINI_TLS12", "0").strip()
        if tls12 not in {"0", "1"}:
            raise ValueError("GEMINI_TLS12 must be 0 or 1")
        return cls(
            api_key=setting("GEMINI_API_KEY").strip(),
            model=setting("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
            mode=mode,
            dataset_path=setting("COMMERCEGRAPH_DATASET") or None,
            tls12=tls12 == "1",
        )
