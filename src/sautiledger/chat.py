"""Typed-utterance REPL — stands in for ASR until phase 3.

Run: python -m sautiledger.chat   (= make chat)
Env: SAUTI_PACK (default pcm-yo-NG), SAUTI_DB (default data/ledger.db)
"""

from __future__ import annotations

import os
import urllib.request

from .agent import Agent
from .ledger import Ledger
from .llm_fallback import OllamaLlmClient
from .packs import load_pack


def _ollama_available() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.5):
            return True
    except Exception:
        return False


def main() -> None:
    pack = load_pack(os.environ.get("SAUTI_PACK", "pcm-yo-NG"))
    ledger = Ledger(os.environ.get("SAUTI_DB", "data/ledger.db"))
    llm = OllamaLlmClient() if _ollama_available() else None
    agent = Agent(pack, ledger, llm)

    print(f"SautiLedger - pack {pack.name} ({pack.currency})")
    print(f"LLM fallback: {'ollama llama3.2:3b' if llm else 'off (grammar-only; Ollama not running)'}")
    print("Type an utterance, or 'quit' to exit.\n")
    while True:
        try:
            text = input("you>   ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in {"quit", "exit"}:
            break
        print(f"sauti> {agent.handle(text)}\n")


if __name__ == "__main__":
    main()
