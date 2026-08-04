"""Deterministic, pack-driven normaliser. Grammar first; the LLM fallback
(llm_fallback.py) is consulted only when the grammar returns None.

The one non-negotiable (CLAUDE.md rule 3): never guess an amount.
Anything outside the known money patterns becomes a clarify intent.
"""

from __future__ import annotations

import re

from .models import ParseResult
from .packs import Pack

_TOKEN_RE = re.compile(r"[a-z0-9']+")

# parse_money sentinels
NO_MONEY = "no_money"
UNPARSEABLE = "unparseable"


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


# ---------------------------------------------------------------- numbers


def _num_value(tok: str, pack: Pack) -> int | None:
    if tok in pack.numbers:
        return pack.numbers[tok]
    if tok.isdigit():
        return int(tok)
    return None


def _knum_value(tok: str) -> int | None:
    m = re.fullmatch(r"(\d+)k", tok)
    return int(m.group(1)) * 1000 if m else None


def is_moneyish(tok: str, pack: Pack) -> bool:
    return (
        _num_value(tok, pack) is not None
        or _knum_value(tok) is not None
        or tok in pack.k_words
        or tok in pack.each_words
        or tok in pack.hard_money_words
    )


def _cls(v: int) -> str:
    if v < 10:
        return "SMALL"
    if v < 100 and v % 10 == 0:
        return "TENS"
    if v == 100:
        return "HUND"
    if v == 1000:
        return "THOU"
    return "OTHER"


def parse_money(tokens: list[str], quantity: int | None, pack: Pack):
    """Resolve a money token run against pack rules only.

    Returns {"amount": n} / {"amount_each": n, "amount": n} on success,
    {"ambiguous": [candidates]} for the distributive trap, or the
    NO_MONEY / UNPARSEABLE sentinels. Never guesses.
    """
    if not tokens:
        return NO_MONEY
    if any(t in pack.hard_money_words for t in tokens):
        return UNPARSEABLE

    each = any(t in pack.each_words for t in tokens)
    toks = [t for t in tokens if t not in pack.each_words]
    if not toks:
        return UNPARSEABLE

    seq: list[tuple[str, int | None]] = []
    for t in toks:
        kv = _knum_value(t)
        if kv is not None:
            seq.append(("KNUM", kv))
            continue
        if t in pack.k_words:
            seq.append(("K", None))
            continue
        v = _num_value(t, pack)
        if v is None:
            return UNPARSEABLE
        seq.append(("NUM", v))

    # compose tens+small pairs: "forty five" -> 45
    comp: list[tuple[str, int | None]] = []
    for kind, v in seq:
        if (
            comp
            and kind == "NUM"
            and comp[-1][0] == "NUM"
            and _cls(comp[-1][1]) == "TENS"
            and _cls(v) == "SMALL"
        ):
            comp[-1] = ("NUM", comp[-1][1] + v)
        else:
            comp.append((kind, v))

    ks = [k for k, _ in comp]
    vs = [v for _, v in comp]
    n = len(comp)
    amount: int | None = None

    if n == 1 and ks == ["KNUM"]:
        amount = vs[0]
    elif n == 2 and ks == ["NUM", "K"]:
        amount = vs[0] * 1000  # "forty five k" -> 45000
    elif n == 3 and ks == ["NUM", "K", "NUM"] and _cls(vs[2]) == "SMALL":
        amount = vs[0] * 1000 + vs[2] * 100  # "five k five" -> 5500
    elif n == 2 and ks == ["NUM", "NUM"]:
        a, b = vs
        ca, cb = _cls(a), _cls(b)
        if cb == "THOU" and a < 1000:
            amount = a * 1000  # "ten thousand"
        elif ca == "THOU" and b < 100:
            amount = b * 1000  # "egberun meta", "elfu tatu", "dubu talatin"
        elif ca == "HUND" and b < 100:
            amount = b * 100 if _cls(b) == "SMALL" else None  # "mia tano"
        elif cb == "HUND" and a < 10:
            amount = a * 100  # "five hundred"
        elif ca == "SMALL" and cb == "SMALL":
            amount = a * 1000 + b * 100  # pair compression: "one two" -> 1200
        elif ca == "SMALL" and cb == "TENS":
            amount = a * 100 + b  # "two fifty" -> 250
    elif n == 3 and ks == ["NUM", "NUM", "NUM"]:
        a, b, c = vs
        ca, cb, cc = _cls(a), _cls(b), _cls(c)
        if ca == "HUND" and cb == "SMALL" and cc == "TENS":
            amount = b * 100 + c  # "mia moja hamsini" -> 150
        elif cb == "HUND" and ca == "SMALL" and cc in ("TENS", "SMALL"):
            amount = a * 100 + c  # "one hundred fifty"
        elif ca == "SMALL" and cb == "SMALL" and cc == "TENS":
            # The distributive trap: "two two fifty" = 250 each, or 2250 total?
            total = a * 1000 + b * 100 + c
            if quantity is not None and a == quantity:
                each_amt = b * 100 + c
                return {
                    "ambiguous": [
                        {"reading": "unit_price", "amount_each": each_amt, "total": each_amt * quantity},
                        {"reading": "total", "amount": total},
                    ]
                }
            return UNPARSEABLE
    elif n == 1 and ks == ["NUM"] and vs[0] >= 100:
        amount = vs[0]  # explicit figure like "500"

    if amount is None:
        return UNPARSEABLE
    if each:
        result: dict = {"amount_each": amount}
        if quantity:
            result["amount"] = amount * quantity
        return result
    return {"amount": amount}


# ---------------------------------------------------------------- phrases


def _find(tokens: list[str], phrase: str) -> int:
    p = phrase.split()
    for i in range(len(tokens) - len(p) + 1):
        if tokens[i : i + len(p)] == p:
            return i
    return -1


def _remove_phrase(tokens: list[str], phrase: str) -> list[str]:
    i = _find(tokens, phrase)
    if i < 0:
        return tokens
    return tokens[:i] + tokens[i + len(phrase.split()) :]


def _find_period(tokens: list[str], pack: Pack) -> str | None:
    for surface, canon in sorted(pack.periods.items(), key=lambda kv: -len(kv[0].split())):
        if _find(tokens, surface) >= 0:
            return canon
    return None


# ---------------------------------------------------------------- intents


def _try_correction(tokens: list[str], pack: Pack) -> ParseResult | None:
    for rule in pack.corrections:
        i = _find(tokens, rule["trigger"])
        if i < 0:
            continue
        if rule["field"] == "amount":
            rest = tokens[i + len(rule["trigger"].split()) :]
            stops = [j for j, t in enumerate(rest) if t in pack.correction_stop_words]
            money_toks = rest[: stops[0]] if stops else rest
            money_toks = [t for t in money_toks if is_moneyish(t, pack)]
            m = parse_money(money_toks, None, pack)
            if isinstance(m, dict) and m.get("amount") is not None:
                return ParseResult(
                    intent="correct_last_entry",
                    field="amount",
                    new_value=m["amount"],
                    currency=pack.currency,
                )
            return ParseResult(intent="clarify", question_about="amount")
        due = next((t for t in tokens if t in pack.days), None)
        return ParseResult(
            intent="correct_last_entry",
            field=rule["field"],
            new_value=rule.get("value"),
            due=due,
        )
    return None


def _try_query(tokens: list[str], pack: Pack) -> ParseResult | None:
    for q in pack.queries:
        if _find(tokens, q["phrase"]) >= 0:
            return ParseResult(
                intent="query_ledger",
                query=q["query"],
                period=_find_period(tokens, pack) or "today",
            )
    return None


def _try_summary(tokens: list[str], pack: Pack) -> ParseResult | None:
    for trigger in pack.summary_triggers:
        if _find(tokens, trigger) >= 0:
            return ParseResult(
                intent="daily_summary",
                period=_find_period(tokens, pack) or "today",
            )
    return None


def _try_transaction(tokens: list[str], pack: Pack) -> ParseResult | None:
    ttype: str | None = None
    triggered = False
    for phrase in pack.expense_triggers:
        if _find(tokens, phrase) >= 0:
            ttype, triggered = "expense", True
            tokens = _remove_phrase(tokens, phrase)
            break
    if ttype is None:
        for phrase in pack.sale_triggers:
            if _find(tokens, phrase) >= 0:
                ttype, triggered = "sale", True
                tokens = _remove_phrase(tokens, phrase)
                break
    if ttype is None:
        for phrase in pack.log_triggers:
            if _find(tokens, phrase) >= 0:
                triggered = True  # generic "log" — default type is sale
                tokens = _remove_phrase(tokens, phrase)
                break

    drop = pack.fillers | pack.currency_words | pack.connectives
    tokens = [t for t in tokens if t not in drop]

    unit: str | None = None
    quantity: int | None = None
    for surface, canon in pack.units_ordered:
        i = _find(tokens, surface)
        if i < 0:
            continue
        unit = canon
        n = len(surface.split())
        before = tokens[i - 1] if i > 0 else None
        after = tokens[i + n] if i + n < len(tokens) else None
        bv = _num_value(before, pack) if before else None
        av = _num_value(after, pack) if after else None
        if bv is not None and bv < 100:
            quantity = bv
            tokens = tokens[: i - 1] + tokens[i + n :]
        elif av is not None and av < 100:
            quantity = av
            tokens = tokens[:i] + tokens[i + n + 1 :]
        else:
            tokens = tokens[:i] + tokens[i + n :]
        break

    j = len(tokens)
    while j > 0 and is_moneyish(tokens[j - 1], pack):
        j -= 1
    money_toks = tokens[j:]
    item = " ".join(tokens[:j]) or None

    if not triggered and unit is None and not money_toks:
        return None  # no transaction signal at all — grammar has no reading

    base = dict(
        type=ttype or "sale",
        item=item,
        quantity=quantity,
        unit=unit,
        currency=pack.currency,
    )

    if item is None and not money_toks and unit is None:
        return ParseResult(intent="clarify", question_about="missing_transaction_details")

    m = parse_money(money_toks, quantity, pack)
    if m in (NO_MONEY, UNPARSEABLE):
        return ParseResult(intent="clarify", question_about="amount", **base)
    if "ambiguous" in m:
        return ParseResult(
            intent="clarify", question_about="amount", candidates=m["ambiguous"], **base
        )
    if item is None:
        # An amount with nothing it belongs to is not a loggable entry.
        return ParseResult(intent="clarify", question_about="missing_transaction_details", **base)
    return ParseResult(
        intent="log_transaction",
        amount=m.get("amount"),
        amount_each=m.get("amount_each"),
        **base,
    )


# ---------------------------------------------------------------- entry


def grammar_parse(utterance: str, pack: Pack) -> ParseResult | None:
    """Deterministic parse. None means the grammar has no reading at all."""
    tokens = tokenize(utterance)
    for attempt in (_try_correction, _try_query, _try_summary, _try_transaction):
        result = attempt(tokens, pack)
        if result is not None:
            return result
    return None


def normalise(utterance: str, pack: Pack, llm=None) -> ParseResult:
    """Grammar first; LLM fallback only when the grammar returns None
    (CLAUDE.md rule 4). The final fallback is a clarify, never a guess."""
    result = grammar_parse(utterance, pack)
    if result is not None:
        return result
    if llm is not None:
        from .llm_fallback import llm_parse  # local import avoids a cycle

        result = llm_parse(utterance, pack, llm)
        if result is not None:
            return result
    return ParseResult(intent="clarify", question_about="missing_transaction_details")
