"""Runtime configuration. Secrets come from the environment or a local
.env file (gitignored — the API key must never be committed)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    pack: str
    db_path: str
    mode: str  # "cloud" | "offline"
    sahara_api_key: str | None
    asr_path: str = "sync"  # "sync" | "async" (async: upload + poll)
    # "auto": local Ollama if running, else grammar-only. "hosted" (remote
    # inference for the fallback step) must be chosen explicitly — utterance
    # text leaving the device is never a silent default.
    agent: str = "auto"  # "auto" | "local" | "hosted" | "none"
    hf_token: str | None = None


def get_settings() -> Settings:
    _load_dotenv(ROOT / ".env")
    key = os.environ.get("SAHARA_API_KEY") or None
    mode = os.environ.get("SAUTI_MODE") or ("cloud" if key else "offline")
    return Settings(
        pack=os.environ.get("SAUTI_PACK", "pcm-yo-NG"),
        db_path=os.environ.get("SAUTI_DB", "data/ledger.db"),
        mode=mode,
        sahara_api_key=key,
        asr_path=os.environ.get("SAUTI_ASR", "sync"),
        agent=os.environ.get("SAUTI_AGENT", "auto"),
        hf_token=os.environ.get("HF_TOKEN") or None,
    )
