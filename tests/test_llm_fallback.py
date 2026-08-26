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


def test_placeholder_question_about_is_sanitised():
    # small models echo the prompt's placeholder — never let junk downstream
    llm = CannedLlm({"intent": "clarify", "question_about": "what is unclear"})
    result = llm_parse(GIBBERISH, PACK, llm)
    assert result.question_about == "missing_transaction_details"


def test_query_with_missing_period_defaults_to_today():
    llm = CannedLlm({"intent": "query_ledger", "query": "profit_or_sales_total"})
    result = llm_parse(GIBBERISH, PACK, llm)
    assert result.period == "today"


def test_amountless_log_transaction_degrades_to_clarify():
    llm = CannedLlm({"intent": "log_transaction", "type": "sale", "item": "rice"})
    result = llm_parse(GIBBERISH, PACK, llm)
    assert result.intent == "clarify" and result.question_about == "amount"
    assert result.item == "rice"  # partial parse kept for the clarify round-trip


def test_unknown_query_or_intent_degrades_to_clarify():
    for payload in (
        {"intent": "query_ledger", "query": "weather_forecast"},
        {"intent": "delete_everything"},
        {"intent": "correct_last_entry"},
    ):
        result = llm_parse(GIBBERISH, PACK, CannedLlm(payload))
        assert result.intent == "clarify", payload


# ------------------------------------------------------- hosted fallback


def test_hosted_client_routes_through_egress_and_is_logged():
    """A hosted fallback call is a remote transmission: it must go through
    EgressRecorder (so it appears in the egress log) and return the
    model's message content."""
    from sautiledger.egress import EgressRecorder
    from sautiledger.ledger import Ledger
    from sautiledger.llm_fallback import HostedLlmClient

    captured = {}

    def fake_open(url, data, headers, timeout, method="POST"):
        captured["url"] = url
        captured["auth"] = headers.get("Authorization")
        body = json.dumps(
            {"choices": [{"message": {"content": '{"intent": "clarify"}'}}]}
        ).encode()
        return 200, body

    ledger = Ledger(":memory:")
    recorder = EgressRecorder(ledger, opener=fake_open)
    client = HostedLlmClient(recorder, token="tok-123")

    out = client.complete("some prompt")
    assert out == '{"intent": "clarify"}'
    assert captured["url"].startswith("https://router.huggingface.co/")
    assert captured["auth"] == "Bearer tok-123"

    log = recorder.log()
    assert len(log) == 1
    assert log[0]["purpose"] == "agent fallback (hosted model)"
    assert log[0]["bytes_sent"] > 0
    assert "delivered" in log[0]["disposition"]


def test_hosted_needs_explicit_opt_in_and_token():
    """"auto" never selects the hosted model — utterance text leaving the
    device must be an explicit choice; and "hosted" without a token
    degrades to grammar-only rather than crashing."""
    from sautiledger.api import _make_llm
    from sautiledger.config import Settings
    from sautiledger.egress import EgressRecorder
    from sautiledger.ledger import Ledger
    from sautiledger.llm_fallback import HostedLlmClient

    recorder = EgressRecorder(Ledger(":memory:"), opener=lambda *a, **k: (200, b"{}"))

    def settings(agent, token):
        return Settings(pack="pcm-yo-NG", db_path=":memory:", mode="offline",
                        sahara_api_key=None, agent=agent, hf_token=token)

    assert _make_llm(settings("none", "tok"), recorder) is None
    assert _make_llm(settings("hosted", None), recorder) is None
    hosted = _make_llm(settings("hosted", "tok"), recorder)
    assert isinstance(hosted, HostedLlmClient)
