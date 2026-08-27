"""Production incident 2026-08-27: spoken '5700' arrived from ASR as
'570007' and reached the ledger as a corrupted amount, read back inside a
garbled 12-word 'item'. These tests replay the exact transcripts and pin
the three structural fixes: the commit gate refuses garbled items on
EVERY path, strange-shape amounts get verified before writing, and the
unknown-item confirm now covers pending-resolution commits too."""

from __future__ import annotations

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack

PACK = load_pack("pcm-yo-NG")

TURN_14 = ("Yeah total eggs purchased yesterday was 2935 so total egg sold "
           "was 285000 so I still have 10 crites left for yesterday that is on the 26")
TURN_17 = ("i sell i bought egg i bought egg yesterday at the rate of i bought "
           "egg yesterday total egg purchase is 2935 Total egg purchase 2935 so "
           "total egg sold yesterday is 2850 2850 so presently i still have 10 great left")


def _agent():
    return Agent(PACK, Ledger(":memory:"))


def test_570007_never_reaches_the_ledger():
    agent = _agent()
    agent.handle(TURN_14)                      # garbled narration -> clarify
    r2 = agent.handle("570007")
    assert "strange shape" in r2               # verified, not written
    assert agent.ledger.entries("today") == []
    r3 = agent.handle("570007")                # trader insists on the figure…
    assert "no write anything" in r3           # …but the garbled item is refused
    assert agent.ledger.entries("today") == [] # NOTHING corrupted was written


def test_293500_expense_with_garbled_item_is_refused():
    agent = _agent()
    agent.handle(TURN_17)
    agent.handle("Total egg purchased is 293,500")
    rows = agent.ledger.entries("today")
    for row in rows:
        assert len((row["item"] or "").split()) <= 4  # no sentence-items, ever


def test_clean_restate_after_refusal_logs_normally():
    agent = _agent()
    agent.handle(TURN_14)
    agent.handle("570007")
    agent.handle("570007")                     # refusal clears the wreckage
    agent.handle("i sell 10 crate of egg for 5700 each")
    rows = agent.ledger.entries("today")
    assert len(rows) == 1
    assert rows[0]["item"] == "egg"
    assert rows[0]["amount_each"] == 5700
    assert rows[0]["amount"] == 57000


def test_round_amounts_keep_zero_friction():
    agent = _agent()
    agent.handle("i don sell 3 crayfish")
    reply = agent.handle("5700")               # 4 digits, round — no guard
    assert "Logged" in reply
    assert agent.ledger.entries("today")[0]["amount"] == 5700

    agent2 = _agent()
    agent2.handle("i don sell 3 crayfish")
    reply = agent2.handle("285000")            # big but round — no guard
    assert "Logged" in reply


def test_insisted_odd_amount_is_accepted_with_clean_item():
    agent = _agent()
    agent.handle("i don sell 3 crayfish")
    assert "strange shape" in agent.handle("10007")
    reply = agent.handle("10007")              # the trader's word wins
    assert "Logged" in reply
    assert agent.ledger.entries("today")[0]["amount"] == 10007


def test_pending_path_now_gets_item_confirm_too():
    """The bypass that let garbage through: resolving a pending amount
    skipped the unknown-item confirm. Now it asks first."""
    agent = _agent()
    agent.handle("i don sell 3 combined space")     # unknown two-word item
    reply = agent.handle("2000")
    assert reply == "Na combined space you talk?"   # confirm BEFORE writing
    assert agent.ledger.entries("today") == []
    agent.handle("yes")
    rows = agent.ledger.entries("today")
    assert len(rows) == 1 and rows[0]["amount"] == 2000


def test_llm_fallback_never_resolves_a_candidates_question():
    """The flattened-distributive guard asks 'each or total?' on purpose.
    A fallback model must never answer that question by itself — even one
    that confidently returns a literal-amount log parse."""
    import json

    from sautiledger.normaliser import normalise

    class EagerLlm:
        def complete(self, prompt):
            return json.dumps({"intent": "log_transaction", "type": "sale",
                               "item": "garri", "quantity": 2, "amount": 250})

    result = normalise("customer take 2 pint of garri 250", PACK, EagerLlm())
    assert result.intent == "clarify"
    assert result.candidates is not None   # the question survives the model
