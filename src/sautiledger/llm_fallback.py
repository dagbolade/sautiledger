"""LLM fallback for utterances the grammar cannot read at all.

Invariant: NEVER fabricate an amount. Two defences here:
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

# The invariant is written into the prompt itself: a wrong entry in someone's
# money records is the worst possible failure, so the model is told that
# clarify is always the safe answer.
FALLBACK_PROMPT = """You turn a market trader's spoken utterance into one JSON object.
Allowed intents: log_transaction, query_ledger, correct_last_entry, daily_summary, clarify.
Schema keys: intent, type (sale|expense), item, quantity, unit, amount, amount_each,
query, period, field, new_value, question_about.

STRICT RULES:
- NEVER invent an amount, quantity, or item. Only use what the utterance states.
- If any detail is unclear, missing, or ambiguous, respond exactly with
  {"intent": "clarify", "question_about": "missing_transaction_details"}
  (question_about must be one of: amount, item, missing_transaction_details).
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
    so the transmission is logged."""

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


def ollama_if_available(timeout: float = 0.5) -> OllamaLlmClient | None:
    """Local Ollama if running, else None (grammar-only). Localhost only —
    never egress."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout):
            return OllamaLlmClient()
    except Exception:
        return None


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

    # Fabrication guard: any amount the model produced must exist literally in
    # the utterance, otherwise the whole parse degrades to clarify.
    allowed = _literal_numbers(utterance, pack)
    amount_fields = [data.get("amount"), data.get("amount_each")]
    if data.get("field") == "amount":
        amount_fields.append(data.get("new_value"))
    for value in amount_fields:
        if value is not None and (not isinstance(value, int) or value not in allowed):
            return ParseResult(intent="clarify", question_about="amount")

    # Confusion guards: a literal-but-wrong pick is still wrong. If the
    # model chose a tiny figure while a money-sized one exists in the same
    # utterance, or picked the quantity as the amount, ask instead.
    amount = data.get("amount")
    if isinstance(amount, int):
        if amount < 100 and any(v >= 100 for v in allowed):
            return ParseResult(intent="clarify", question_about="amount")
        if amount == data.get("quantity"):
            return ParseResult(intent="clarify", question_about="amount")

    try:
        result = ParseResult(**data)
    except TypeError:
        return None

    # Sanitise small-model sloppiness so downstream tools never see junk.
    if result.intent == "clarify":
        if result.question_about not in {"amount", "item", "missing_transaction_details"}:
            result.question_about = "missing_transaction_details"
    elif result.intent == "query_ledger":
        if result.query not in {"profit_or_sales_total", "top_item", "credit_outstanding"}:
            return ParseResult(intent="clarify", question_about="missing_transaction_details")
        result.period = result.period or "today"
    elif result.intent == "daily_summary":
        result.period = result.period or "today"
    elif result.intent == "correct_last_entry":
        # field must be real and new_value present — never NULL out a ledger column
        if (
            result.field not in {"amount", "amount_each", "item", "quantity", "unit", "payment_status"}
            or result.new_value is None
        ):
            return ParseResult(intent="clarify", question_about="missing_transaction_details")
        # a correction needs a correction cue in the words — chatter must
        # never mutate the ledger through the fallback
        cue_words = {"no", "not", "wrong", "na", "change", "correct"}
        if not any(t in cue_words for t in re.findall(r"[a-z']+", utterance.lower())):
            return ParseResult(intent="clarify", question_about="missing_transaction_details")
        # a corrected item name must come from the utterance, not the model
        if result.field == "item" and str(result.new_value).lower() not in utterance.lower():
            return ParseResult(intent="clarify", question_about="missing_transaction_details")
    elif result.intent == "log_transaction":
        # completeness side of the invariant: no amount -> not a loggable entry
        if result.amount is None and result.amount_each is None:
            return ParseResult(
                intent="clarify", question_about="amount",
                type=result.type, item=result.item,
                quantity=result.quantity, unit=result.unit,
                currency=pack.currency,
            )
        result.currency = pack.currency
    else:
        return ParseResult(intent="clarify", question_about="missing_transaction_details")
    return result
