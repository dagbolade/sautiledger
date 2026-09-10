import pytest

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack


def book():
    return Agent(load_pack("pcm-yo-NG"), Ledger(":memory:"))


def test_purchase_and_sale_go_to_separate_totals_with_explicit_readback():
    a = book()
    assert "Logged sale:" in a.handle("I sell 5 crate of egg for 2000 naira each")
    assert a.handle("Yes, you get") == "Noted. Ledger correct."
    assert not a.awaiting_confirm and a.pending is None
    reply = a.handle("I go market go buy 5 carton of indomie for 3000 naira each")
    assert "Logged expense:" in reply and "fifteen thousand naira total" in reply
    a.handle("yes")
    assert a.ledger.sales_total("today")[1] == 10000
    assert a.ledger.expenses_total("today")[1] == 15000


@pytest.mark.parametrize("answer, expected", [("each", 15000), ("total", 3000), ("4000 each", 20000)])
def test_eight_is_a_question_not_an_automatic_each_substitution(answer, expected):
    a = book()
    a.handle("I go market go market today i buy 5 carton of windomin for my stock for 3000 8")
    assert a.pending.type == "expense" and a.pending.question_about == "price_basis"
    assert not a.ledger.all_transactions()
    a.handle("yes")  # yes alone doesn't choose a price interpretation
    assert not a.ledger.all_transactions() and a.pending is not None
    reply = a.handle(answer)
    assert "Logged expense:" in reply
    assert a.ledger.last_transaction()["amount"] == expected
    assert a.ledger.sales_total("today")[1] == 0


@pytest.mark.parametrize("text", [
    "I sell 2 carton of indomie for yaboki for 5000 naira",
    "I go market go buy 5 carton of indomie for 5 for 3000 naira each",
])
def test_buyer_or_damaged_quantity_cannot_be_confirmed_as_part_of_item(text):
    a = book()
    a.handle(text)
    assert a.pending.question_about == "transaction_details"
    a.handle("yes")
    assert not a.ledger.all_transactions()
    a.handle("I go market go buy 5 carton of indomie for 3000 naira each")
    row = a.ledger.last_transaction()
    assert (row["item"], row["type"], row["amount"]) == ("indomie", "expense", 15000)


def test_restatement_after_each_question_replaces_all_old_details():
    a = book()
    a.handle("I buy 5 carton of rice for 3000 8")
    a.handle("I buy 2 carton of indomie for 4000 naira each")
    row = a.ledger.last_transaction()
    assert (row["quantity"], row["item"], row["amount"]) == (2, "indomie", 8000)


def test_customer_buy_remains_a_sale():
    a = book()
    a.handle("customer buy 5 carton of indomie for 3000 naira each")
    assert a.ledger.last_transaction()["type"] == "sale"
