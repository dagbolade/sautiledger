"""Positive-path tests against the REAL llama3.2:3b — no mocks.

Excluded from `make test` (pytest addopts -m 'not live'); run explicitly:
  make test-live   (= python -m pytest -m live -q)

Every test asserts on LEDGER STATE, not just reply text. Fresh in-memory
DB per test. If these fail, fix the pipeline — never loosen the asserts.
"""

from __future__ import annotations

import pytest

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.llm_fallback import ollama_if_available
from sautiledger.packs import load_pack

pytestmark = pytest.mark.live


@pytest.fixture
def agent():
    llm = ollama_if_available()
    if llm is None:
        pytest.skip("Ollama is not running at 127.0.0.1:11434")
    return Agent(load_pack("pcm-yo-NG"), Ledger(":memory:"), llm)


def _rows(agent):
    return agent.ledger.entries("today")


# (a) positive-path sale
def test_sale_logs_exactly_one_correct_row(agent):
    reply = agent.handle("I don sell three derica of rice five thousand five")
    rows = _rows(agent)
    assert len(rows) == 1
    row = rows[0]
    assert row["type"] == "sale"
    assert row["item"] == "rice"
    assert row["quantity"] == 3
    assert row["unit"] == "derica"
    assert row["amount"] == 5500
    assert row["currency"] == "NGN"
    assert "five thousand five hundred" in reply


# (b) reduplication distributive — confident one-turn log (native-validated)
def test_reduplication_logs_in_one_turn(agent):
    reply = agent.handle("customer take two paint rubber of garri two two fifty")
    rows = _rows(agent)
    assert len(rows) == 1
    assert rows[0]["amount_each"] == 250
    assert rows[0]["amount"] == 500
    assert "two hundred fifty" in reply


# (b2) case 21: the natural clarify beat — no row until the amount arrives
def test_amountless_sale_clarify_round_trip(agent):
    reply = agent.handle("I don sell garri finish")
    assert "How much" in reply and "?" in reply
    assert len(_rows(agent)) == 0  # nothing written before the answer

    agent.handle("five thousand")
    rows = _rows(agent)
    assert len(rows) == 1
    assert rows[0]["item"] == "garri"
    assert rows[0]["amount"] == 5000


# (c) query sums exactly the rows created, writes nothing
def test_query_sums_ledger_exactly(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    agent.handle("customer take two paint rubber of garri two two fifty")
    assert len(_rows(agent)) == 2

    reply = agent.handle("how much I make today")
    assert "six thousand naira" in reply  # 5500 + 500
    assert len(_rows(agent)) == 2  # queries never write


# (b3) v2 flattened-distributive guard: both resolutions
def test_flattened_guard_resolves_each(agent):
    reply = agent.handle("customer take 2 pint of garri 250")
    assert "each one" in reply and "?" in reply
    assert len(_rows(agent)) == 0
    agent.handle("each")
    rows = _rows(agent)
    assert len(rows) == 1
    assert rows[0]["amount_each"] == 250 and rows[0]["amount"] == 500


def test_flattened_guard_resolves_total(agent):
    agent.handle("customer take 2 pint of garri 250")
    assert len(_rows(agent)) == 0
    agent.handle("na total")
    rows = _rows(agent)
    assert len(rows) == 1
    assert rows[0]["amount"] == 250 and rows[0]["amount_each"] is None


# (c2) item-filtered query — asks the ledger, never logs
def test_item_filtered_query(agent):
    agent.handle("I sell groundnut 3 for 500")
    assert len(_rows(agent)) == 1
    reply = agent.handle("how much groundnut I don sell today")
    assert "groundnut" in reply.lower() and "five hundred naira" in reply
    assert len(_rows(agent)) == 1  # a question never writes


# (c3) the no-echo rule: clarify questions never parrot the utterance
def test_clarify_never_echoes_utterance(agent):
    rambling = "I don sell the thing wey that woman carry come here yesterday evening"
    reply = agent.handle(rambling)
    assert "?" in reply
    assert len(reply) < 90  # short fixed template
    assert "woman carry come" not in reply  # no parroting
    assert len(_rows(agent)) == 0


# (d) chatter never mutates the ledger
def test_chatter_leaves_ledger_unchanged(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    before = [dict(r) for r in _rows(agent)]
    for utterance in (
        "my friend how your body today",
        "customer wan come back tomorrow for the thing",
        "abeg make you help me remember say I get meeting",
    ):
        agent.handle(utterance)
        agent.pending = None  # each chatter line stands alone
    after = [dict(r) for r in _rows(agent)]
    assert after == before  # row count AND contents unchanged
