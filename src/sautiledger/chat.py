"""Typed-utterance REPL — drives the agent without a microphone.

Run: python -m sautiledger.chat   (= make chat)
Env: SAUTI_PACK (default pcm-yo-NG), SAUTI_DB (default data/ledger.db)
"""

from __future__ import annotations

import os

from .agent import Agent
from .ledger import Ledger
from .llm_fallback import ollama_if_available
from .packs import load_pack


def main() -> None:
    pack = load_pack(os.environ.get("SAUTI_PACK", "pcm-yo-NG"))
    ledger = Ledger(os.environ.get("SAUTI_DB", "data/ledger.db"))
    llm = ollama_if_available()
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
