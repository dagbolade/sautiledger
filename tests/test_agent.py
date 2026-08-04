"""End-to-end agent tests over the spec cases: utterance in, spoken reply
out, ledger rows checked. Uses an in-memory DB and a raising LLM — the
whole flow must work grammar-only."""

from __future__ import annotations

import pytest

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack


class RaisingLlm:
    def complete(self, prompt: str) -> str:
        raise AssertionError("LLM fallback consulted in e2e flow")


@pytest.fixture
def agent():
    return Agent(load_pack("pcm-yo-NG"), Ledger(":memory:"), llm=RaisingLlm())


def _rows(agent):
    return agent.ledger.entries("today")


# case 1
def test_sale_with_k_slang(agent):
    reply = agent.handle("I don sell three derica of rice five thousand five")
    assert "rice" in reply and "five thousand five hundred naira" in reply
    row = agent.ledger.last_transaction()
    assert row["amount"] == 5500 and row["quantity"] == 3 and row["unit"] == "derica"


# case 3
def test_expense(agent):
    agent.handle("I buy fuel ten thousand naira")
    row = agent.ledger.last_transaction()
    assert row["type"] == "expense" and row["amount"] == 10000 and row["item"] == "fuel"


# case 4 — reduplication distributive logs CONFIDENTLY (native-validated)
def test_reduplication_distributive_logs_directly(agent):
    reply = agent.handle("customer take two paint rubber of garri two two fifty")
    rows = _rows(agent)
    assert len(rows) == 1  # no clarify round trip: native grammar is unambiguous
    row = rows[0]
    assert row["amount_each"] == 250 and row["amount"] == 500 and row["quantity"] == 2
    assert "two hundred fifty" in reply and "each" in reply


# case 21 — the natural clarify beat: sale completed, amount unspoken
def test_amountless_sale_asks_then_logs(agent):
    reply = agent.handle("I don sell garri finish")
    assert "How much you sell the garri?" == reply
    assert len(_rows(agent)) == 0  # MUST NOT log until the amount arrives
    agent.handle("five thousand")
    row = agent.ledger.last_transaction()
    assert row["item"] == "garri" and row["amount"] == 5000


# case 5
def test_yoruba_numeral(agent):
    agent.handle("sell garri egberun meta")
    assert agent.ledger.last_transaction()["amount"] == 3000


# case 8
def test_query_total(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    agent.handle("sell garri egberun meta")
    reply = agent.handle("abeg how much I don make today")
    assert "eight thousand five hundred naira" in reply and "2 sales" in reply


# case 10
def test_amount_correction(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    agent.handle("no no na five k not five thousand five")
    assert agent.ledger.last_transaction()["amount"] == 5000


# case 11
def test_credit_correction(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    reply = agent.handle("that one na credit she go pay on Friday")
    row = agent.ledger.last_transaction()
    assert row["payment_status"] == "credit" and row["due"] == "friday"
    assert "credit" in reply


# case 12
def test_daily_summary(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    agent.handle("I buy fuel ten thousand naira")
    reply = agent.handle("close the day give me summary")
    assert "1 sale" in reply and "five thousand five hundred naira in" in reply
    assert "ten thousand naira out" in reply


# case 13
def test_multiword_item(agent):
    agent.handle("sell pure water two bag one two")
    row = agent.ledger.last_transaction()
    assert row["item"] == "pure water" and row["amount"] == 1200


# case 20 — the no-content guard
def test_empty_log_request_never_writes(agent):
    reply = agent.handle("log am make I hear")
    assert "?" in reply
    assert len(_rows(agent)) == 0
    assert agent.ledger.last_transaction() is None


def test_agent_refuses_amountless_log(agent):
    """Belt-and-braces on rule 3: even if a parse reaches dispatch with no
    amount, the agent asks instead of writing."""
    from sautiledger.models import ParseResult

    reply = agent._dispatch(
        ParseResult(intent="log_transaction", type="sale", item="rice", currency="NGN"),
        "raw",
    )
    assert "?" in reply
    assert agent.ledger.last_transaction() is None


def test_amount_clarify_then_answer(agent):
    """Case-6-style flow: unparseable Yoruba money -> ask -> answer -> log."""
    reply = agent.handle("oya log am one congo of crayfish egbeje o din owo")
    assert "crayfish" in reply and "?" in reply
    assert len(_rows(agent)) == 0
    agent.handle("one four")
    row = agent.ledger.last_transaction()
    assert row["item"] == "crayfish" and row["amount"] == 1400
