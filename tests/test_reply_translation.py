"""English-reply translation must survive punctuation edits.

english_reply() maps Pidgin reply templates to English by pattern. On
14 September a punctuation clean-up changed some agent strings and their
patterns differently, and four replies silently stayed in Pidgin for
English-mode users. No test noticed; only the conversation benchmark diff
did. These tests drive the real agent to each reply shape and assert the
English rendering contains no Pidgin.
"""

from __future__ import annotations

import pytest

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack
from sautiledger.replies import english_reply

PIDGIN_MARKERS = ("make i", "wetin", "wahala", "you don", "abeg", "talk am", "no fit", "never make")


def _agent():
    return Agent(load_pack("pcm-yo-NG"), Ledger(":memory:"), llm=None)


def _assert_english(reply: str):
    english = english_reply(reply)
    lowered = english.lower()
    assert not any(m in lowered for m in PIDGIN_MARKERS), f"untranslated: {english!r}"
    return english


def test_amount_check_question_translates():
    a = _agent()
    reply = a.handle("I buy fuel thousand naira")
    assert "Please check" in _assert_english(reply)


def test_net_balance_positive_translates():
    a = _agent()
    a.handle("I sell rice 5000 naira"); a.handle("yes")
    a.handle("I buy fuel 1000 naira"); a.handle("yes")
    assert "Sales less expenses" in _assert_english(a.handle("wetin remain"))


def test_net_balance_negative_translates():
    a = _agent()
    a.handle("I buy fuel 10000 naira"); a.handle("yes")
    assert "Expenses exceed sales" in _assert_english(a.handle("wetin remain"))


def test_profit_query_translates():
    a = _agent()
    a.handle("I sell rice 5000 naira"); a.handle("yes")
    a.handle("I buy fuel 1000 naira"); a.handle("yes")
    _assert_english(a.handle("how much i don make today"))


@pytest.mark.parametrize("sep", [":", ","])
def test_fixed_strings_translate_with_either_punctuation(sep):
    for reply in (
        f"Network wahala{sep} I no fit reach the cloud right now. Try again small time.",
        f"I hear five thousand naira{sep} that number get strange shape. Abeg talk the amount one more time make I sure.",
        f"Wetin I hear no clear at all, so I no write anything. Abeg talk am again{sep} just the item and the amount.",
    ):
        _assert_english(reply)
