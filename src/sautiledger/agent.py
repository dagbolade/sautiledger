"""The agent loop: transcript -> normaliser -> {tool dispatch | clarify}.

Turn state is one pending ParseResult held in memory — nothing beyond
the ledger is ever persisted.
"""

from __future__ import annotations

from dataclasses import replace

from . import tools
from .ledger import Ledger
from .models import ParseResult
from .normaliser import grammar_parse, is_moneyish, normalise, parse_money, tokenize
from .packs import Pack

_YES_WORDS = {"yes", "yeah", "yep", "correct", "ok", "okay", "sure"}
_NO_WORDS = {"no", "nope"}
# longest first — matched as leading token sequences
_YES_PHRASES = [["na", "so"], ["na", "him"], ["e", "correct"]]
_NO_PHRASES = [
    ["i", "no", "talk", "that", "one"], ["i", "no", "talk"],
    ["you", "no", "hear"], ["no", "be", "so"], ["no", "be"],
]


def _strip_leading(toks: list[str], words: set[str], phrases: list[list[str]]):
    """Strip a leading yes/no marker; returns (remainder, matched)."""
    for phrase in phrases:
        if toks[: len(phrase)] == phrase:
            return toks[len(phrase):], True
    if toks and toks[0] in words:
        rest = toks[1:]
        while rest and rest[0] in words:  # "no no …"
            rest = rest[1:]
        return rest, True
    return toks, False


def _strip_copula(toks: list[str]) -> list[str]:
    """After a rejection, 'na …' introduces the restatement ('no, na 2
    biscuits for 350') — drop the copula so it never pollutes the parse.
    'na so' / 'na him' are affirmations, not copulas: leave those."""
    if len(toks) >= 2 and toks[0] == "na" and toks[1] not in ("so", "him"):
        return toks[1:]
    return toks


class Agent:
    def __init__(self, pack: Pack, ledger: Ledger, llm=None):
        self.pack = pack
        self.ledger = ledger
        self.llm = llm
        self.pending: ParseResult | None = None
        self.awaiting_confirm = False
        self.last_logged_id: int | None = None
        # strange-shape amount already queried once — repeating it is consent
        self._odd_amount_offered: int | None = None

    def handle(self, text: str) -> str:
        if self.pending is not None:
            reply = self._try_resolve_pending(text)
            if reply is not None:
                return reply
            self.pending = None  # answer didn't fit — treat as a fresh utterance
        was_confirming = False
        if self.awaiting_confirm:
            self.awaiting_confirm = False
            was_confirming = True
            handled = self._handle_confirmation(text)
            if handled is not None:
                return handled
        parse = normalise(text, self.pack, self.llm)
        if (
            was_confirming
            and self.last_logged_id is not None
            and parse.intent == "clarify"
            and parse.item is None
            and parse.amount is None
            and parse.amount_each is None
            and tokenize(text)[:1] == ["na"]
        ):
            # a copula-led confirm-time reply with nothing loggable in it
            # ("Na Michael come") is a detail note on the entry, not a new
            # transaction — the money already captured must survive. The
            # copula is the cue (same rule as corrections); cue-less chatter
            # still never touches the ledger.
            return self._note_on_last(text)
        return self._dispatch(parse, text)

    def _note_on_last(self, text: str) -> str:
        row = self.ledger.append_note(self.last_logged_id, text)
        if row is None:
            return "Wetin you want make I log? Tell me the item and the amount, abeg."
        what = row["item"] or "entry"
        money = tools._money(row["amount"] or 0, row["currency"])
        return (f"I don note am. The entry still stand: {what}, {money}. "
                f"If something wrong, talk 'no, na …' make I fix am.")

    def _handle_confirmation(self, text: str) -> str | None:
        """A reply to '… Correct?' may reject, confirm, or carry new content
        in the same breath. A rejection VOIDS the just-logged row first —
        the ledger must never keep an entry the user refused."""
        # a full correction ("no no na five thousand") fixes in place and
        # outranks yes/no stripping
        quick = grammar_parse(text, self.pack)
        if quick is not None and quick.intent == "correct_last_entry":
            return self._dispatch(quick, text)

        toks = tokenize(text)
        rest, rejected = _strip_leading(toks, _NO_WORDS, _NO_PHRASES)
        if rejected:
            self._void_last_logged()
            rest = _strip_copula(rest)
            if not rest:
                return "I don remove am. Wetin I write wrong? Talk am again."
            return self.handle(" ".join(rest))  # remainder is the replacement
        rest, confirmed = _strip_leading(toks, _YES_WORDS, _YES_PHRASES)
        if confirmed:
            if not rest:
                return "Noted. Ledger correct."
            return self.handle(" ".join(rest))  # fresh utterance, same breath
        return None  # not a confirmation — process normally

    def _void_last_logged(self) -> None:
        if self.last_logged_id is not None:
            self.ledger.void_transaction(self.last_logged_id)
            self.last_logged_id = None

    # ------------------------------------------------------------ dispatch

    def _dispatch(self, parse: ParseResult, raw: str) -> str:
        if parse.intent == "log_transaction":
            if parse.amount is None and parse.amount_each is None:
                # second layer of the never-fabricate invariant:
                # nothing amountless is ever written
                parse = replace(parse, intent="clarify", question_about="amount")
                self.pending = parse
                return self._clarify_question(parse)
            return self._gate_and_commit(parse, raw)
        if parse.intent == "query_ledger":
            return tools.query_ledger(
                self.ledger, parse.query, parse.period, self.pack.currency, item=parse.item
            )
        if parse.intent == "correct_last_entry":
            return tools.correct_last_entry(
                self.ledger, parse.field, parse.new_value, parse.due, self.pack.currency
            )
        if parse.intent == "daily_summary":
            return tools.daily_summary(
                self.ledger, parse.period, self.pack.currency,
                recap=(parse.query == "recap"),
            )
        # clarify: hold the partial parse and ask
        self.pending = parse
        return self._clarify_question(parse)

    # a real item name is a few words; a sentence in the item slot is a
    # mis-parse ("was 285000 so still have 10 crites left…", production
    # incident 2026-08-27) — never written, never read back as "Correct?"
    _MAX_ITEM_WORDS = 4

    def _item_is_garbled(self, item: str | None) -> bool:
        if not item:
            return False
        core = [w for w in item.split() if w not in self.pack.descriptors]
        return len(core) > self._MAX_ITEM_WORDS

    def _gate_and_commit(self, parse: ParseResult, raw: str) -> str:
        """The single gate in front of EVERY write — dispatch and every
        pending-resolution path alike. A garbled item is refused outright:
        offering 'Correct?' on an incoherent readback invites a tired yes
        onto a corrupted row."""
        if self._item_is_garbled(parse.item):
            self.pending = None
            return ("Wetin I hear no clear at all, so I no write anything. "
                    "Abeg talk am again — just the item and the amount.")
        if self._needs_item_confirm(parse):
            # suspicious item name: confirm BEFORE anything is written
            self.pending = replace(parse, intent="clarify", question_about="item_confirm")
            return f"Na {parse.item} you talk?"
        return self._commit(parse, raw)

    def _commit(self, parse: ParseResult, raw: str) -> str:
        reply = tools.log_transaction(self.ledger, parse, raw)
        row = self.ledger.last_transaction()
        self.last_logged_id = row["id"] if row else None
        self.awaiting_confirm = True  # the readback ends "Correct?"
        return reply

    def _needs_item_confirm(self, parse: ParseResult) -> bool:
        """Multi-word item names the pack has never heard of and this ledger
        has never logged ("combined space", "to buy") are usually ASR
        debris — those get confirmed before commit. Known items and single
        new words (real products like "biscuits") log normally."""
        if not parse.item:
            return False
        # descriptors are detail, not doubt: "big egg" is one item word
        core = [w for w in parse.item.split() if w not in self.pack.descriptors]
        if len(core) <= 1:
            return False
        if parse.item in self.pack.multi_word_items:
            return False
        return not self.ledger.has_logged_item(parse.item)

    def _clarify_question(self, parse: ParseResult) -> str:
        if parse.candidates:
            unit_price = next(c for c in parse.candidates if c["reading"] == "unit_price")
            total = next(c for c in parse.candidates if c["reading"] == "total")
            if unit_price["amount_each"] == total["amount"]:
                # flattened-distributive guard: one figure, two readings
                spoken = tools.spoken_number(total["amount"])
                return f"Na {spoken} naira for each one, or {spoken} naira for everything?"
            thing = parse.item or "that one"
            return (
                f"The {thing} - you mean {tools.spoken_number(unit_price['amount_each'])} each "
                f"({tools.spoken_number(unit_price['total'])} total), or "
                f"{tools.spoken_number(total['amount'])} total?"
            )
        if parse.question_about == "amount":
            # NO-ECHO RULE: never rebuild the user's utterance inside our own
            # question — a mangled parse would parrot garbage back. Only a
            # short, clean item name may be mentioned; otherwise fixed template.
            if parse.item and len(parse.item.split()) <= 3:
                verb = "pay for" if parse.type == "expense" else "sell"
                return f"How much you {verb} the {parse.item}?"
            return "How much you sell am?"
        if parse.question_about == "item":
            return "Wetin she buy? Talk the thing name."
        return "Wetin you want make I log? Tell me the item and the amount, abeg."

    # ------------------------------------------------------------ clarify flow

    def _try_resolve_pending(self, text: str) -> str | None:
        pending = self.pending
        lowered = tokenize(text)

        if pending.question_about == "item_confirm":
            rest, confirmed = _strip_leading(lowered, _YES_WORDS, _YES_PHRASES)
            if confirmed and not rest:
                self.pending = None
                return self._commit(
                    replace(pending, intent="log_transaction", question_about=None), text
                )
            rest, rejected = _strip_leading(lowered, _NO_WORDS, _NO_PHRASES)
            if rejected:
                self.pending = None  # nothing was written
                rest = _strip_copula(rest)
                if not rest:
                    return "Oya talk am again make I hear well."
                return self.handle(" ".join(rest))  # rejection + restatement
            return None  # they restated instead — parse it fresh

        if pending.candidates:
            chosen = None
            if "each" in lowered:
                chosen = next(c for c in pending.candidates if c["reading"] == "unit_price")
            elif "total" in lowered or "all" in lowered:
                chosen = next(c for c in pending.candidates if c["reading"] == "total")
            if chosen is None:
                return None
            self.pending = None
            filled = replace(
                pending,
                intent="log_transaction",
                question_about=None,
                candidates=None,
                amount=chosen.get("total", chosen.get("amount")),
                amount_each=chosen.get("amount_each"),
            )
            return self._gate_and_commit(filled, text)

        if pending.question_about == "amount" and pending.item:
            money_toks = [t for t in lowered if is_moneyish(t, self.pack)]
            # the answer to "how much?" IS the amount: small figures count,
            # and the distributive guard doesn't re-ask
            m = parse_money(money_toks, pending.quantity, self.pack, total_marked=True)
            if isinstance(m, dict) and "ambiguous" not in m:
                amount = m.get("amount")
                if (
                    amount is not None and amount >= 10000 and amount % 50
                    and amount != self._odd_amount_offered
                ):
                    # ASR digit-merge signature: spoken "5700" arrived as
                    # "570007" (production incident 2026-08-27). Big and
                    # not ending in a round figure — verify before writing.
                    # Repeating the same figure accepts it: the trader's
                    # word wins over the heuristic.
                    self._odd_amount_offered = amount
                    return (f"I hear {tools.spoken_number(amount)} naira — "
                            f"that number get strange shape. Abeg talk the "
                            f"amount one more time make I sure.")
                self._odd_amount_offered = None
                self.pending = None
                filled = replace(
                    pending,
                    intent="log_transaction",
                    question_about=None,
                    amount=amount,
                    amount_each=m.get("amount_each"),
                )
                return self._gate_and_commit(filled, text)

        if pending.question_about == "item" and (pending.amount or pending.amount_each):
            words = [t for t in lowered
                     if t not in self.pack.fillers and not is_moneyish(t, self.pack)]
            if words and len(words) <= 4:
                self.pending = None
                filled = replace(
                    pending, intent="log_transaction", question_about=None,
                    item=" ".join(words),
                )
                return self._gate_and_commit(filled, text)
        return None
