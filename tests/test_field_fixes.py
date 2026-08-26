"""Field-testing round one: three real gaps from David's and his sister's
drafts — 'worth' as a money connective, confirm-time notes that keep the
captured money, and the typed-shorthand register ('Mr olaolu 1big egg @5700')."""

from __future__ import annotations

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.normaliser import grammar_parse, tokenize
from sautiledger.packs import load_pack

PACK = load_pack("pcm-yo-NG")


def _agent():
    return Agent(PACK, Ledger(":memory:"))


# ---------------------------------------------------- 1. worth/cost/goes for


def test_worth_marks_an_explicit_total():
    r = grammar_parse("i sell egg worth 12000 naira", PACK)
    assert r.intent == "log_transaction"
    assert r.item == "egg"
    assert r.amount == 12000


def test_cost_and_goes_for_parse_like_for():
    r = grammar_parse("i sell 2 crate of egg cost 11000", PACK)
    assert r.intent == "log_transaction"
    assert (r.item, r.quantity, r.unit, r.amount) == ("egg", 2, "crate", 11000)

    r = grammar_parse("garri goes for 500", PACK)
    assert r.intent == "log_transaction"
    assert (r.item, r.amount) == ("garri", 500)


# ------------------------------------- 2. confirm-time note keeps the money


def test_garbled_confirm_reply_becomes_a_note_not_a_restart():
    agent = _agent()
    agent.handle("i don sell 3 crayfish for 2000 naira")  # -> "Correct?"
    reply = agent.handle("na michale come")
    rows = agent.ledger.entries("today")
    assert len(rows) == 1
    assert rows[0]["payment_status"] == "paid"       # never voided
    assert rows[0]["amount"] == 2000                 # money survived
    assert "[note: na michale come]" in rows[0]["raw_utterance"]
    assert "still stand" in reply and "two thousand naira" in reply


def test_real_rejection_still_voids_and_replaces():
    agent = _agent()
    agent.handle("i don sell 3 crayfish for 2000 naira")
    agent.handle("no, na 2 crayfish for 2000 naira")
    rows = agent.ledger.entries("today")
    statuses = sorted(r["payment_status"] for r in rows)
    assert statuses == ["paid", "voided"]            # the flow is untouched
    live = [r for r in rows if r["payment_status"] == "paid"][0]
    assert live["quantity"] == 2


def test_plain_yes_confirmation_untouched():
    agent = _agent()
    agent.handle("i don sell 3 crayfish for 2000 naira")
    assert agent.handle("yes") == "Noted. Ledger correct."


# --------------------------------------------- 3. typed shorthand register


def test_shorthand_buyer_qty_descriptor_at_price():
    r = grammar_parse("Mr olaolu 1big egg @5700", PACK)
    assert r.intent == "log_transaction"
    assert r.quantity == 1
    assert r.item == "big egg"
    assert r.amount == 5700


def test_shorthand_logs_without_item_confirm_detour():
    agent = _agent()
    reply = agent.handle("Mr olaolu 1big egg @5700")
    rows = agent.ledger.entries("today")
    assert len(rows) == 1
    assert rows[0]["amount"] == 5700
    assert "five thousand seven hundred" in reply


def test_at_with_space_and_small_descriptor():
    r = grammar_parse("madam bisi 2small crate of egg @ 3000", PACK)
    assert r.intent == "log_transaction"
    assert (r.quantity, r.unit, r.amount) == (2, "crate", 3000)


def test_shorthand_never_guesses_a_bad_amount():
    # hard-money phrase after "@" still refuses to value — clarify, no guess
    r = grammar_parse("oga sam 2big egg @ egbeje o din owo", PACK)
    assert r.intent == "clarify"
    assert r.question_about == "amount"
    assert r.amount is None


def test_money_tokens_survive_the_glue_split():
    assert tokenize("5.5k") == ["5.5k"]
    assert tokenize("sell garri 5k") == ["sell", "garri", "5k"]
    assert tokenize("1big egg @5700") == ["1", "big", "egg", "at", "5700"]


def test_cueless_chatter_during_confirm_never_touches_the_row():
    agent = _agent()
    agent.handle("i don sell 3 crayfish for 2000 naira")
    before = [dict(r) for r in agent.ledger.entries("today")]
    agent.handle("my friend how your body today")
    after = [dict(r) for r in agent.ledger.entries("today")]
    assert after == before  # no note, no void — cue-less chatter is inert
