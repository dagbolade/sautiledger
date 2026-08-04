"""The fallback's rule-3 guard: an LLM may never invent an amount."""

from __future__ import annotations

import json

from sautiledger.llm_fallback import llm_parse
from sautiledger.normaliser import grammar_parse, normalise
from sautiledger.packs import load_pack

PACK = load_pack("pcm-yo-NG")
GIBBERISH = "how you dey my friend"  # no triggers, no numbers — no grammar reading


class CannedLlm:
    def __init__(self, payload: dict):
        self.payload = payload

    def complete(self, prompt: str) -> str:
        return json.dumps(self.payload)


def test_gibberish_has_no_grammar_reading():
    assert grammar_parse(GIBBERISH, PACK) is None


def test_invented_amount_is_discarded():
    llm = CannedLlm(
        {"intent": "log_transaction", "type": "sale", "item": "rice", "amount": 5000}
    )
    result = llm_parse(GIBBERISH, PACK, llm)
    assert result.intent == "clarify"
    assert result.amount is None


def test_llm_clarify_passes_through():
    llm = CannedLlm({"intent": "clarify", "question_about": "missing_transaction_details"})
    result = llm_parse(GIBBERISH, PACK, llm)
    assert result.intent == "clarify"
    assert result.question_about == "missing_transaction_details"


def test_llm_query_without_amount_is_accepted():
    llm = CannedLlm({"intent": "query_ledger", "query": "top_item", "period": "today"})
    result = llm_parse(GIBBERISH, PACK, llm)
    assert result.intent == "query_ledger"
    assert result.query == "top_item"


def test_no_llm_means_clarify_not_crash():
    result = normalise(GIBBERISH, PACK, llm=None)
    assert result.intent == "clarify"
