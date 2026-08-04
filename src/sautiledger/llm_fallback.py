"""LLM fallback for utterances the grammar cannot read at all.

CLAUDE.md rule 3: NEVER fabricate an amount. Two defences here:
  1. FALLBACK_PROMPT orders the model to return clarify when unsure.
  2. llm_parse() discards any amount that is not literally present in
     the utterance (as digits or a single pack number word) and
     degrades the result to a clarify intent.
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Protocol

from .models import ParseResult
from .packs import Pack

# Rule 3 lives in the prompt itself: a confident wrong entry in someone's
# money records is the worst possible failure, so the model is told that
# clarify is always the safe answer.
FALLBACK_PROMPT = """You turn a market trader's spoken utterance into one JSON object.
Allowed intents: log_transaction, query_ledger, correct_last_entry, daily_summary, clarify.
Schema keys: intent, type (sale|expense), item, quantity, unit, amount, amount_each,
query, period, field, new_value, question_about.

STRICT RULES:
- NEVER invent an amount, quantity, or item. Only use what the utterance states.
- If any detail is unclear, missing, or ambiguous, respond exactly with
  {"intent": "clarify", "question_about": "<what is unclear>"}.
- A wrong amount in a money ledger is worse than asking again. When in doubt: clarify.
- Respond with the JSON object only, no prose.

Utterance: {utterance}
JSON:"""

_ALLOWED_KEYS = {
    "intent", "type", "item", "quantity", "unit", "amount", "amount_each",
    "query", "period", "field", "new_value", "question_about",
}


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str: ...


class OllamaLlmClient:
    """Local model via Ollama. NOTE: this talks to localhost only — it is
    not network egress. Any REMOTE llm must route through egress.py
    (phase 3) per CLAUDE.md rule 2."""

    def __init__(self, model: str = "llama3.2:3b", host: str = "http://127.0.0.1:11434"):
        self.model = model
        self.host = host

    def complete(self, prompt: str) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["response"]


def _literal_numbers(utterance: str, pack: Pack) -> set[int]:
    """Every number literally present in the utterance: digit tokens,
    digit+k tokens, and single pack number words."""
    allowed: set[int] = set()
    for tok in re.findall(r"[a-z0-9']+", utterance.lower()):
        if tok.isdigit():
            allowed.add(int(tok))
        m = re.fullmatch(r"(\d+)k", tok)
        if m:
            allowed.add(int(m.group(1)) * 1000)
        if tok in pack.numbers:
            allowed.add(pack.numbers[tok])
    return allowed


def llm_parse(utterance: str, pack: Pack, llm: LlmClient) -> ParseResult | None:
    try:
        raw = llm.complete(FALLBACK_PROMPT.replace("{utterance}", utterance))
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
    except Exception:
        return None
    if not isinstance(data, dict) or "intent" not in data:
        return None

    data = {k: v for k, v in data.items() if k in _ALLOWED_KEYS}

    # Rule 3 guard: any amount the model produced must exist literally in
    # the utterance, otherwise the whole parse degrades to clarify.
    allowed = _literal_numbers(utterance, pack)
    amount_fields = [data.get("amount"), data.get("amount_each")]
    if data.get("field") == "amount":
        amount_fields.append(data.get("new_value"))
    for value in amount_fields:
        if value is not None and (not isinstance(value, int) or value not in allowed):
            return ParseResult(intent="clarify", question_about="amount")

    try:
        result = ParseResult(**data)
    except TypeError:
        return None
    if result.intent == "log_transaction":
        result.currency = pack.currency
    return result
