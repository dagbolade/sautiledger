import pytest

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack


def book():
    return Agent(load_pack("pcm-yo-NG"), Ledger(":memory:"))


@pytest.mark.parametrize("amount", ["220 naira", "300 naira"])
def test_bare_amount_during_readback_keeps_original_confirmation(amount):
    a = book()
    a.handle("i sell biscuits 220 naira for iya chinonso")
    reply = a.handle(amount)
    assert "Correct?" in reply
    assert a.awaiting_confirm and a.pending is None
    assert a.handle("yes") == "Noted. Ledger correct."
    rows = a.ledger.all_transactions()
    assert len(rows) == 1
    assert (rows[0]["item"], rows[0]["amount"]) == ("biscuits", 220)


@pytest.mark.parametrize("answer", ["yes", "no", "okay", "beeni", "na so", "Yes, you get"])
def test_confirmation_is_not_an_item_and_real_item_can_follow(answer):
    a = book()
    a.handle("220 naira")
    assert a.pending.question_about == "item"
    a.handle(answer)
    assert not a.ledger.all_transactions()
    assert a.pending.question_about == "item" and a.pending.amount == 220
    a.handle("biscuits")
    rows = a.ledger.all_transactions()
    assert len(rows) == 1
    assert (rows[0]["item"], rows[0]["amount"]) == ("biscuits", 220)


def test_repeated_amount_still_allows_rejection_and_replacement():
    a = book()
    a.handle("i sell biscuits for 220 naira")
    a.handle("220 naira")
    a.handle("no")
    a.handle("i sell biscuits for 300 naira")
    a.handle("yes")
    assert a.ledger.sales_total("today")[1] == 300


def test_new_explicit_sale_during_readback_is_still_recorded():
    a = book()
    a.handle("i sell biscuits for 220 naira")
    a.handle("i sell rice for 500 naira")
    assert a.ledger.sales_total("today")[1] == 720


@pytest.mark.parametrize("correction", ["no, na five thousand", "no, na fuel five thousand", "no no na five thousand"])
def test_expense_correction_preserves_direction_and_audit(correction):
    a = book()
    a.handle("I buy fuel ten thousand naira")
    reply = a.handle(correction)
    assert "Correct?" in reply
    rows = a.ledger.all_transactions()
    assert len(rows) == 2
    assert rows[0]["amount"] == 10000 and rows[0]["payment_status"] == "voided"
    assert rows[1]["type"] == "expense" and rows[1]["amount"] == 5000
    assert a.ledger.sales_total("today")[1] == 0
    a.handle("no")
    assert a.ledger.expenses_total("today")[1] == 0


def test_amount_revision_keeps_credit_metadata_and_other_book_untouched():
    a = book()
    a.handle("I sell 2 cup of rice for 500 naira each")
    a.ledger.correct_last("payment_status", "credit", "tomorrow")
    other = a.ledger.scoped("other-book")
    from sautiledger.models import ParseResult
    other.add_transaction(ParseResult(intent="log_transaction", type="sale", item="egg", amount=100, currency="NGN"), "test")
    a.ledger.correct_last("amount", 800)
    rows = a.ledger.all_transactions()
    assert len(rows) == 2 and rows[0]["amount"] == 1000
    assert rows[0]["payment_status"] == "voided"
    assert rows[1]["payment_status"] == "credit" and rows[1]["due"] == "tomorrow"
    assert rows[1]["amount_each"] is None
    assert other.last_transaction()["amount"] == 100
