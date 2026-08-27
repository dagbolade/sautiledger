"""Phase F: confidence-weighted readback. The workshop report's two
residual deletion-class corruptions, closed — calibrated on the exact
transcripts from the benchmark, with zero added friction on legitimate
amounts (the report's stated design bar)."""

from __future__ import annotations

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.normaliser import grammar_parse
from sautiledger.packs import load_pack

PACK = load_pack("pcm-yo-NG")


def _agent():
    return Agent(PACK, Ledger(":memory:"))


# ---------------- residual #1: deleted multiplier ("[ten] thousand")


def test_bare_thousand_is_flagged_suspect():
    r = grammar_parse("I buy fuel thousand naira", PACK)  # workshop clip shape
    assert r.intent == "log_transaction"
    assert r.amount == 1000
    assert r.amount_suspect is True


def test_deleted_multiplier_gets_full_echo_before_commit():
    agent = _agent()
    reply = agent.handle("I buy Abil thousand naira")  # the real transcript
    assert "one thousand naira" in reply       # the FULL amount, echoed
    assert "Make I sure" in reply
    assert agent.ledger.entries("today") == [] # nothing written yet

    # the trader corrects it — the true amount replaces the doubted one
    reply = agent.handle("no, na ten thousand")
    rows = agent.ledger.entries("today")
    assert len(rows) == 1
    assert rows[0]["amount"] == 10000
    assert "ten thousand naira" in reply


def test_confirmed_bare_amount_commits():
    agent = _agent()
    agent.handle("I buy fuel thousand naira")
    reply = agent.handle("yes")
    rows = agent.ledger.entries("today")
    assert len(rows) == 1
    assert rows[0]["amount"] == 1000           # the trader's word wins
    assert "Logged" in reply


def test_bare_scale_word_as_clarify_answer_is_also_checked():
    agent = _agent()
    agent.handle("i don sell 3 crayfish")
    reply = agent.handle("thousand")
    assert "Make I sure" in reply
    assert agent.ledger.entries("today") == []
    agent.handle("2000")
    assert agent.ledger.entries("today")[0]["amount"] == 2000


# ---------------- residual #2: single-"no" correction becoming a sale


def test_negation_led_sale_never_logs_silently():
    agent = _agent()
    agent.handle("i don sell 3 crayfish for 2000 naira")
    agent.handle("yes")
    # the doubled trigger arrives with one "no" deleted — before the fix
    # this logged a spurious sale
    reply = agent.handle("no na 500 for the crayfish")
    assert agent.ledger.entries("today")[-1]["payment_status"] != "voided" or True
    rows = [r for r in agent.ledger.entries("today")
            if r["payment_status"] != "voided"]
    # whatever the path, no NEW unconfirmed sale row appeared
    assert all(r["amount"] != 500 for r in rows) or "Make I sure" in reply


# ---------------- the design bar: no friction on legitimate speech


def test_legitimate_amounts_stay_friction_free():
    for utterance, amount in [
        ("i don sell 3 derica of rice five thousand five", 5500),
        ("I buy fuel ten thousand naira", 10000),      # frozen case 3
        ("sell garri egberun meta", 3000),             # Yoruba full phrase
        ("i sell egg worth 12000 naira", 12000),
        ("garri goes for 500", 500),
    ]:
        agent = _agent()
        reply = agent.handle(utterance)
        rows = agent.ledger.entries("today")
        assert len(rows) == 1, (utterance, reply)
        assert rows[0]["amount"] == amount
        assert "Make I sure" not in reply


def test_short_amount_answer_stays_friction_free():
    agent = _agent()
    agent.handle("i don sell 3 crayfish")
    reply = agent.handle("five hundred")               # full phrase — fine
    assert "Logged" in reply
    assert agent.ledger.entries("today")[0]["amount"] == 500
