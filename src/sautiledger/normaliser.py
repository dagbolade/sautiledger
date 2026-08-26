"""Deterministic, pack-driven normaliser. Grammar first; the LLM fallback
(llm_fallback.py) is consulted only when the grammar returns None.

The one non-negotiable: never guess an amount.
Anything outside the known money patterns becomes a clarify intent.
"""

from __future__ import annotations

import re

from .models import ParseResult
from .packs import Pack

# "5.5k" survives as one token; "5,500" loses its comma first
_TOKEN_RE = re.compile(r"\d+\.\d+k|[a-z0-9']+")
_DIGIT_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")
# typed-shorthand glue: "1big egg" -> "1 big egg". Two-letter minimum so
# "5k" / "5.5k" money tokens survive intact.
_QTY_GLUE_RE = re.compile(r"(?<=\d)(?=[a-z]{2,})")

# parse_money sentinels
NO_MONEY = "no_money"
UNPARSEABLE = "unparseable"


def tokenize(text: str) -> list[str]:
    # written-shorthand register: "@5700" is the typed price marker —
    # same tier as the spoken connectives (for/at/worth)
    text = text.lower().replace("@", " at ")
    text = _QTY_GLUE_RE.sub(" ", text)
    return _TOKEN_RE.findall(_DIGIT_COMMA_RE.sub("", text))


# ---------------------------------------------------------------- numbers


def _num_value(tok: str, pack: Pack) -> int | None:
    if tok in pack.numbers:
        return pack.numbers[tok]
    if tok.isdigit():
        return int(tok)
    return None


def _knum_value(tok: str) -> int | None:
    # digit-k forms incl. decimals: Sahara's numeric normalisation may emit
    # "5k" / "5.5k" regardless of what was spoken
    m = re.fullmatch(r"(\d+(?:\.\d+)?)k", tok)
    return int(float(m.group(1)) * 1000) if m else None


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


def _money_value(toks: list[str], pack: Pack) -> int | None:
    """Value a plain (non-reduplicated) money phrase, or None."""
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
            return None
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

    if n == 1 and ks == ["KNUM"]:
        return vs[0]  # "5k", "5.5k"
    if n == 2 and ks == ["KNUM", "NUM"] and _cls(vs[1]) == "SMALL" and pack.digit_twin_thousands:
        # Digit-twin of the native "N thousand M" form —
        # Sahara's numeric normalisation emits "5k 5" for spoken
        # "five thousand five"; refusing it was the grammar not speaking
        # Sahara's output dialect, not safety.
        return vs[0] + vs[1] * 100
    if n == 2 and ks == ["NUM", "K"]:
        return vs[0] * 1000  # "forty five k" -> 45000
    if n == 2 and ks == ["NUM", "NUM"]:
        a, b = vs
        ca, cb = _cls(a), _cls(b)
        if cb == "THOU" and a < 1000:
            return a * 1000  # "ten thousand"
        if ca == "THOU" and b < 100:
            return b * 1000  # "egberun meta", "elfu tatu", "dubu talatin"
        if ca == "HUND" and _cls(b) == "SMALL":
            return b * 100  # "mia tano"
        if cb == "HUND" and a < 10:
            return a * 100  # "five hundred"
        if ca == "SMALL" and cb == "SMALL":
            return a * 1000 + b * 100  # pair compression: "one two" -> 1200
        if ca == "SMALL" and cb == "TENS":
            return a * 100 + b  # "two fifty" -> 250
        return None
    if n == 3 and ks == ["NUM", "NUM", "NUM"]:
        a, b, c = vs
        ca, cb, cc = _cls(a), _cls(b), _cls(c)
        if cb == "THOU" and a < 1000 and cc == "SMALL":
            # native-validated: "<N> thousand <M>" = N*1000 + M*100
            # ("five thousand five" -> 5500; "three thousand two" -> 3200)
            return a * 1000 + c * 100
        if ca == "HUND" and cb == "SMALL" and cc == "TENS":
            return b * 100 + c  # "mia moja hamsini" -> 150
        if cb == "HUND" and ca == "SMALL" and cc in ("TENS", "SMALL"):
            return a * 100 + c  # "one hundred fifty"
        return None
    if n == 1 and ks == ["NUM"] and vs[0] >= 100:
        return vs[0]  # explicit figure like "500" / "5500"
    return None


def _small_single_value(toks: list[str], pack: Pack) -> int | None:
    """A lone figure under 100 ('biscuits FOR 50 naira'): only money when a
    price connective vouched for it (total_marked callers only)."""
    if len(toks) == 1:
        v = _num_value(toks[0], pack)
        if v is not None and 0 < v < 100:
            return v
    return None


def parse_money(tokens: list[str], quantity: int | None, pack: Pack, total_marked: bool = False):
    """Resolve a money token run against pack rules only.

    Returns {"amount": n} / {"amount_each": n, "amount": n} on success,
    {"ambiguous": [candidates]} for genuinely ambiguous forms, or the
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

    def _each_result(value: int) -> dict:
        result: dict = {"amount_each": value}
        if quantity:
            result["amount"] = value * quantity
        return result

    # Reduplication distributive (native-speaker validated, pack-gated):
    # a doubled money amount means per-unit price. Full-phrase doubling
    # ("two fifty two fifty", "hundred hundred") or leading-token doubling
    # ("two two fifty" -> two-fifty each; "one one thousand" -> 1000 each).
    if pack.reduplication_distributive and len(toks) >= 2:
        half = len(toks) // 2
        if len(toks) % 2 == 0 and toks[:half] == toks[half:]:
            inner = _money_value(toks[:half], pack)
            if inner is not None:
                return _each_result(inner)
        if toks[0] == toks[1]:
            inner = _money_value(toks[1:], pack)
            if inner is not None:
                return _each_result(inner)

    amount = _money_value(toks, pack)
    if amount is None and total_marked:
        # "for 50 naira": the connective marks even a small figure as money
        amount = _small_single_value(toks, pack)
    if amount is not None:
        if each:
            return _each_result(amount)
        if quantity is not None and quantity >= 2 and len(toks) == 1 and not total_marked:
            # Flattened-distributive guard: ASR numeric
            # normalisation can collapse reduplication ("two two fifty" ->
            # "250") before the grammar sees it. A single bare numeral with
            # quantity >= 2 is unknowable: each, or total? Ask, never guess.
            return {
                "ambiguous": [
                    {"reading": "unit_price", "amount_each": amount, "total": amount * quantity},
                    {"reading": "total", "amount": amount},
                ]
            }
        return {"amount": amount}
    if amount is None:
        # [SMALL, SMALL, TENS] without the reduplication rule (non-pcm packs)
        # stays the ambiguity trap: ask, never guess.
        vals = [_num_value(t, pack) for t in toks]
        if (
            len(vals) == 3
            and all(v is not None for v in vals)
            and _cls(vals[0]) == "SMALL" and _cls(vals[1]) == "SMALL" and _cls(vals[2]) == "TENS"
            and quantity is not None and vals[0] == quantity
        ):
            each_amt = vals[1] * 100 + vals[2]
            total = vals[0] * 1000 + vals[1] * 100 + vals[2]
            return {
                "ambiguous": [
                    {"reading": "unit_price", "amount_each": each_amt, "total": each_amt * quantity},
                    {"reading": "total", "amount": total},
                ]
            }
        return UNPARSEABLE


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


def _try_interrogative(tokens: list[str], pack: Pack) -> ParseResult | None:
    """Interrogative + sale trigger = a QUERY, never a transaction:
    'how much groundnut I don sell today' asks the ledger, it does not
    log a sale. Leftover content words become an item filter."""
    if not any(_find(tokens, phrase) >= 0 for phrase in pack.interrogatives):
        return None
    period = _find_period(tokens, pack) or "today"
    rest = list(tokens)
    for phrase in (list(pack.interrogatives) + pack.sale_triggers
                   + pack.expense_triggers + pack.log_triggers
                   + list(pack.periods)):
        rest = _remove_phrase(rest, phrase)
    drop = pack.fillers | pack.currency_words | pack.connectives | pack.days
    leftover = [t for t in rest if t not in drop and _num_value(t, pack) is None]
    if leftover:
        return ParseResult(
            intent="query_ledger", query="item_total",
            item=" ".join(leftover), period=period,
        )
    return ParseResult(intent="query_ledger", query="profit_or_sales_total", period=period)


def _try_recap(tokens: list[str], pack: Pack) -> ParseResult | None:
    """Full row-by-row readback. Runs BEFORE the interrogative pass so
    'wetin dey my ledger' reads the book instead of querying an item, and
    matches loosely — 'read ALL my ledger for today' must not miss because
    of an interposed word."""
    for trigger in pack.recap_triggers:
        if _find(tokens, trigger) >= 0:
            return ParseResult(
                intent="daily_summary", query="recap",
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
    def consume_trigger(toks: list[str], phrases: list[str]) -> tuple[list[str], bool]:
        for phrase in phrases:
            i = _find(toks, phrase)
            if i >= 0:
                # everything BEFORE the trigger is narration ("Blessing come
                # my shop come buy…") — names get ASR-mangled, so the prefix
                # is discarded rather than parsed
                return toks[i + len(phrase.split()):], True
        return toks, False

    ttype: str | None = None
    tokens, triggered = consume_trigger(tokens, pack.expense_triggers)
    if triggered:
        ttype = "expense"
    else:
        tokens, triggered = consume_trigger(tokens, pack.sale_triggers)
        if triggered:
            ttype = "sale"
        else:
            tokens, triggered = consume_trigger(tokens, pack.log_triggers)
            # generic "log" — default type is sale

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
    item_toks = tokens[:j]

    # "groundnut 3 FOR 500": a price connective before the amount marks the
    # figure as an explicit total (skip the distributive guard)
    total_marked = False
    while item_toks and item_toks[-1] in pack.price_connectives:
        item_toks.pop()
        total_marked = True

    if quantity is None and len(item_toks) >= 2:
        lead = _num_value(item_toks[0], pack)
        trail = _num_value(item_toks[-1], pack)
        if lead is not None and 1 <= lead <= 99:
            # Quantity recovery, "N item" order: ASR can mangle the unit
            # word ("2 pint of dairy") so the numeral lands in item position
            quantity = lead
            item_toks = item_toks[1:]
        elif trail is not None and 1 <= trail <= 99:
            # "item N" order: "groundnut 3 for 500" -> qty 3, item groundnut
            quantity = trail
            item_toks = item_toks[:-1]

    if total_marked and quantity is None:
        # typed-shorthand register: "Mr olaolu 1 big egg at 5700" — with an
        # explicit price marker present, the first count-sized numeral is
        # the quantity, and whatever precedes it is a buyer/narration
        # prefix (names arrive ASR-mangled, never required to parse)
        for idx, tok in enumerate(item_toks):
            v = _num_value(tok, pack)
            if v is not None and 1 <= v <= 99:
                quantity = v
                item_toks = item_toks[idx + 1:]
                break

    if total_marked and quantity is None and len(money_toks) == 1 and item_toks:
        # amount-for-quantity order: "biscuits 350 for 2" = ₦350 for 2 —
        # a count-sized figure after the connective with a money-sized
        # figure before it means the sides are swapped
        small = _num_value(money_toks[0], pack)
        big = _num_value(item_toks[-1], pack)
        if small is not None and 1 <= small <= 99 and big is not None and big >= 100:
            quantity = small
            money_toks = [item_toks.pop()]
    item = " ".join(item_toks) or None

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

    m = parse_money(money_toks, quantity, pack, total_marked=total_marked)
    if m in (NO_MONEY, UNPARSEABLE):
        return ParseResult(intent="clarify", question_about="amount", **base)
    if "ambiguous" in m:
        return ParseResult(
            intent="clarify", question_about="amount", candidates=m["ambiguous"], **base
        )
    if item is None:
        # An amount with nothing it belongs to is not loggable — but there IS
        # a transaction signal, so ask about the item, not the generic prompt.
        return ParseResult(
            intent="clarify", question_about="item",
            amount=m.get("amount"), amount_each=m.get("amount_each"), **base,
        )
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
    for attempt in (_try_correction, _try_query, _try_recap, _try_interrogative, _try_summary, _try_transaction):
        result = attempt(tokens, pack)
        if result is not None:
            return result
    return None


def normalise(utterance: str, pack: Pack, llm=None) -> ParseResult:
    """Grammar first; LLM fallback only when the grammar returns None —
    or, for LONG utterances with a transaction signal the grammar could
    not complete, as a second reading (the sanitiser in
    llm_fallback.py still forbids any amount not literally present).
    The final fallback is a clarify, never a guess."""
    result = grammar_parse(utterance, pack)
    if result is not None:
        if llm is not None and result.intent == "clarify" and result.question_about == "amount":
            tokens = tokenize(utterance)
            # Widened fallback for narrated speech: >6 words, no deliberate
            # hard-money refusal in play. Never fires on the frozen clarify
            # cases (6: hard words; 20/21: short / different question).
            if len(tokens) > 6 and not any(t in pack.hard_money_words for t in tokens):
                from .llm_fallback import llm_parse

                llm_result = llm_parse(utterance, pack, llm)
                if llm_result is not None and llm_result.intent == "log_transaction":
                    return llm_result
        return result
    if llm is not None:
        from .llm_fallback import llm_parse  # local import avoids a cycle

        result = llm_parse(utterance, pack, llm)
        if result is not None:
            return result
    return ParseResult(intent="clarify", question_about="missing_transaction_details")
