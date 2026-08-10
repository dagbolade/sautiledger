"""End-to-end agent tests over the corpus cases: utterance in, spoken reply
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
    """Second layer of the never-fabricate invariant: even if a parse has no
    amount, the agent asks instead of writing."""
    from sautiledger.models import ParseResult

    reply = agent._dispatch(
        ParseResult(intent="log_transaction", type="sale", item="rice", currency="NGN"),
        "raw",
    )
    assert "?" in reply
    assert agent.ledger.last_transaction() is None


def test_confirmation_yes_with_new_content(agent):
    """'yes, and then …' — confirm and process the rest in one breath."""
    agent.handle("I don sell three derica of rice five thousand five")
    reply = agent.handle("yes and I sell garri egberun meta")
    assert "three thousand naira" in reply
    assert len(_rows(agent)) == 2


def test_confirmation_bare_yes(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    reply = agent.handle("yes")
    assert "Noted" in reply
    assert len(_rows(agent)) == 1


def test_confirmation_bare_no_voids_and_prompts(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    reply = agent.handle("no")
    assert "wrong" in reply.lower()
    assert agent.ledger.last_transaction() is None  # rejected row voided
    assert agent.ledger.sales_total("today") == (0, 0)


def test_rejection_with_replacement_voids_then_relogs(agent):
    """'No, I don say…' must never leave the rejected row in the book."""
    agent.handle("I don sell three derica of rice five thousand five")
    agent.handle("no I don sell garri egberun meta")
    rows = _rows(agent)
    live_rows = [r for r in rows if r["payment_status"] != "voided"]
    assert len(live_rows) == 1
    assert live_rows[0]["item"] == "garri" and live_rows[0]["amount"] == 3000


def test_unknown_multiword_item_confirms_before_commit(agent):
    reply = agent.handle("customer buy combined space for 300")
    assert reply == "Na combined space you talk?"
    assert len(_rows(agent)) == 0  # NOTHING written yet
    agent.handle("yes")
    row = agent.ledger.last_transaction()
    assert row["item"] == "combined space" and row["amount"] == 300


def test_unknown_multiword_item_rejected_writes_nothing(agent):
    agent.handle("customer buy combined space for 300")
    agent.handle("no")
    assert len(_rows(agent)) == 0
    assert agent.ledger.last_transaction() is None


def test_known_multiword_item_logs_directly(agent):
    agent.handle("sell pure water two bag one two")  # pack-known item
    assert agent.ledger.last_transaction()["item"] == "pure water"


def test_recap_matches_loose_phrasings(agent):
    """Lagos-prep regression: 'read ALL my ledger for today' and other
    ledger mentions must reach the recap, never the LLM fallback."""
    agent.handle("i sell 2 carton of indomie for 25000 naira")
    for phrasing in ("read all my ledger for today", "check my ledger", "wetin dey my ledger"):
        reply = agent.handle(phrasing)
        assert "indomie" in reply and "twenty five thousand naira" in reply, phrasing


def test_recap_reads_the_book(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    agent.handle("yes")
    agent.handle("sell garri egberun meta")
    reply = agent.handle("read my ledger")
    assert "rice" in reply and "garri" in reply
    assert "eight thousand five hundred naira" in reply  # 5500 + 3000


def test_correction_outranks_confirmation_stripping(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    agent.handle("no no na five k not five thousand five")
    assert agent.ledger.last_transaction()["amount"] == 5000


def test_narrated_amountless_then_answer(agent):
    reply = agent.handle("Blessing come my shop come buy biscuits")
    assert reply == "How much you sell the biscuits?"
    assert len(_rows(agent)) == 0
    agent.handle("50 naira")
    row = agent.ledger.last_transaction()
    assert row["item"] == "biscuits" and row["amount"] == 50


def test_void_transaction(agent):
    agent.handle("I don sell three derica of rice five thousand five")
    txn_id = agent.ledger.last_transaction()["id"]
    agent.ledger.void_transaction(txn_id)
    assert agent.ledger.last_transaction() is None  # voided rows invisible
    assert agent.ledger.sales_total("today") == (0, 0)
    # but never silently erased: the row persists, marked voided
    raw = agent.ledger.conn.execute(
        "SELECT payment_status FROM transactions WHERE id = ?", (txn_id,)
    ).fetchone()
    assert raw["payment_status"] == "voided"


def test_amount_for_quantity_order(agent):
    """Lagos-prep regression: 'biscuits 350 for 2' = ₦350 for 2 pieces."""
    reply = agent.handle("i sell biscuits 350 for 2")
    row = agent.ledger.last_transaction()
    assert row["item"] == "biscuits" and row["quantity"] == 2 and row["amount"] == 350
    assert "three hundred fifty naira" in reply


def test_item_confirm_rejection_with_restatement(agent):
    """Lagos-prep regression: 'no, na 2 biscuits for 350 naira' must strip
    the negation AND the copula, then log the restatement cleanly."""
    agent.handle("customer buy combined space for 300")  # -> item confirm
    assert len(_rows(agent)) == 0
    reply = agent.handle("no, na 2 biscuits for 350 naira")
    row = agent.ledger.last_transaction()
    assert row["item"] == "biscuits" and row["quantity"] == 2 and row["amount"] == 350
    assert "no na" not in reply


def test_carton_market_unit(agent):
    """Lagos-prep regression: 'carton' must be a known unit, not item debris."""
    reply = agent.handle("i sell 2 carton of indomie for 25000 naira")
    row = agent.ledger.last_transaction()
    assert row["item"] == "indomie" and row["quantity"] == 2 and row["unit"] == "carton"
    assert row["amount"] == 25000
    assert "2 carton of indomie" in reply


def test_amount_clarify_then_answer(agent):
    """Case-6-style flow: unparseable Yoruba money -> ask -> answer -> log."""
    reply = agent.handle("oya log am one congo of crayfish egbeje o din owo")
    assert "crayfish" in reply and "?" in reply
    assert len(_rows(agent)) == 0
    agent.handle("one four")
    row = agent.ledger.last_transaction()
    assert row["item"] == "crayfish" and row["amount"] == 1400
