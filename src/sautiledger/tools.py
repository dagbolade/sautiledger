"""Exactly four tools (CLAUDE.md: do not add a fifth). All replies are
short and spoken-style, echoing amount and item so the TTS readback
doubles as verification of what was written to the ledger."""

from __future__ import annotations

from .ledger import Ledger
from .models import ParseResult

_CURRENCY_WORDS = {"NGN": "naira", "KES": "shillings"}

_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_TEENS = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
          "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _below_thousand(n: int) -> str:
    parts = []
    if n >= 100:
        parts.append(f"{_ONES[n // 100]} hundred")
        n %= 100
    if n >= 20:
        word = _TENS[n // 10]
        if n % 10:
            word += f" {_ONES[n % 10]}"
        parts.append(word)
    elif n >= 10:
        parts.append(_TEENS[n - 10])
    elif n:
        parts.append(_ONES[n])
    return " ".join(parts)


def spoken_number(n: int) -> str:
    """Integers 0..999_999 as spoken words, for readback."""
    if n == 0:
        return "zero"
    parts = []
    if n >= 1000:
        parts.append(f"{_below_thousand(n // 1000)} thousand")
        n %= 1000
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def _money(amount: int, currency: str) -> str:
    return f"{spoken_number(amount)} {_CURRENCY_WORDS.get(currency, currency)}"


# ------------------------------------------------------------------ tools


def log_transaction(ledger: Ledger, parse: ParseResult, raw_utterance: str) -> str:
    ledger.add_transaction(parse, raw_utterance)
    what = parse.item or "entry"
    if parse.quantity and parse.unit:
        what = f"{parse.quantity} {parse.unit} of {parse.item}"
    verb = "Logged expense" if parse.type == "expense" else "Logged"
    if parse.amount_each and parse.amount:
        return (
            f"{verb}: {what}, {_money(parse.amount_each, parse.currency)} each, "
            f"{_money(parse.amount, parse.currency)} total. Correct?"
        )
    if parse.amount_each:  # per-unit price with unknown quantity
        return f"{verb}: {what}, {_money(parse.amount_each, parse.currency)} each. Correct?"
    return f"{verb}: {what}, {_money(parse.amount, parse.currency)}. Correct?"


def query_ledger(ledger: Ledger, query: str, period: str | None, currency: str) -> str:
    period = period or "today"
    when = "this week" if period == "this_week" else period
    if query == "top_item":
        top = ledger.top_item(period)
        if top is None:
            return f"No sales logged {when} yet."
        item, total = top
        return f"Your best seller {when} na {item}, {_money(total, currency)}."
    if query == "credit_outstanding":
        total = ledger.credit_outstanding()
        if not total:
            return "Nobody dey owe you. Credit book clean."
        return f"Credit outstanding: {_money(total, currency)}."
    # default: profit_or_sales_total
    n, total = ledger.sales_total(period)
    if n == 0:
        return f"No sales logged {when} yet."
    return f"You don make {_money(total, currency)} from {n} sale{'s' if n != 1 else ''} {when}."


def correct_last_entry(
    ledger: Ledger, field: str, new_value, due: str | None = None, currency: str | None = None
) -> str:
    row = ledger.correct_last(field, new_value, due)
    if row is None:
        return "Nothing to correct yet — no entry in the ledger."
    if field == "amount":
        return f"Corrected: {row['item'] or 'last entry'} now {_money(new_value, row['currency'])}. Correct?"
    if field == "payment_status":
        due_part = f", she go pay {due}" if due else ""
        return f"Noted: last entry na {new_value}{due_part}. I dey watch am."
    return f"Corrected: {field} now {new_value}."


def daily_summary(ledger: Ledger, period: str | None, currency: str) -> str:
    period = period or "today"
    sales_n, sales_total = ledger.sales_total(period)
    exp_n, exp_total = ledger.expenses_total(period)
    credit = ledger.credit_outstanding()
    when = "this week" if period == "this_week" else period
    parts = [f"{sales_n} sale{'s' if sales_n != 1 else ''}, {_money(sales_total, currency)} in"]
    if exp_n:
        parts.append(f"{exp_n} expense{'s' if exp_n != 1 else ''}, {_money(exp_total, currency)} out")
    if credit:
        parts.append(f"credit outstanding {_money(credit, currency)}")
    return f"Summary for {when}: " + "; ".join(parts) + "."
