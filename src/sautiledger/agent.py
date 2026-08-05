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

_YES_WORDS = {"yes", "yeah", "yep", "correct", "ok", "okay"}
_NO_WORDS = {"no", "nope"}


class Agent:
    def __init__(self, pack: Pack, ledger: Ledger, llm=None):
        self.pack = pack
        self.ledger = ledger
        self.llm = llm
        self.pending: ParseResult | None = None
        self.awaiting_confirm = False

    def handle(self, text: str) -> str:
        if self.pending is not None:
            reply = self._try_resolve_pending(text)
            if reply is not None:
                return reply
            self.pending = None  # answer didn't fit — treat as a fresh utterance
        if self.awaiting_confirm:
            self.awaiting_confirm = False
            handled = self._handle_confirmation(text)
            if handled is not None:
                return handled
        parse = normalise(text, self.pack, self.llm)
        return self._dispatch(parse, text)

    def _handle_confirmation(self, text: str) -> str | None:
        """Reply to '… Correct?' may carry new content in the same breath:
        'yes, and then Sarah come buy…'. Strip the yes/no, keep going."""
        # a full correction ("no no na five thousand") outranks the stripping
        quick = grammar_parse(text, self.pack)
        if quick is not None and quick.intent == "correct_last_entry":
            return self._dispatch(quick, text)

        toks = tokenize(text)
        if toks[:2] == ["na", "so"]:  # Pidgin yes
            toks = toks[2:]
            confirmed = True
        elif toks and toks[0] in _YES_WORDS:
            toks = toks[1:]
            confirmed = True
        elif toks and toks[0] in _NO_WORDS:
            toks = toks[1:]
            if not toks:
                return "Wetin I write wrong? Talk am — like 'no no na five thousand'."
            confirmed = False
        else:
            return None  # not a confirmation — process normally
        if not toks:
            return "Noted. Ledger correct." if confirmed else None
        # remainder is a fresh utterance in the same breath
        return self.handle(" ".join(toks))

    # ------------------------------------------------------------ dispatch

    def _dispatch(self, parse: ParseResult, raw: str) -> str:
        if parse.intent == "log_transaction":
            if parse.amount is None and parse.amount_each is None:
                # belt-and-braces on rule 3: nothing amountless is written
                parse = replace(parse, intent="clarify", question_about="amount")
                self.pending = parse
                return self._clarify_question(parse)
            self.awaiting_confirm = True  # readback ends "Correct?"
            return tools.log_transaction(self.ledger, parse, raw)
        if parse.intent == "query_ledger":
            return tools.query_ledger(
                self.ledger, parse.query, parse.period, self.pack.currency, item=parse.item
            )
        if parse.intent == "correct_last_entry":
            return tools.correct_last_entry(
                self.ledger, parse.field, parse.new_value, parse.due, self.pack.currency
            )
        if parse.intent == "daily_summary":
            return tools.daily_summary(self.ledger, parse.period, self.pack.currency)
        # clarify: hold the partial parse and ask
        self.pending = parse
        return self._clarify_question(parse)

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
            return tools.log_transaction(self.ledger, filled, text)

        if pending.question_about == "amount" and pending.item:
            money_toks = [t for t in lowered if is_moneyish(t, self.pack)]
            # the answer to "how much?" IS the amount: small figures count,
            # and the distributive guard doesn't re-ask
            m = parse_money(money_toks, pending.quantity, self.pack, total_marked=True)
            if isinstance(m, dict) and "ambiguous" not in m:
                self.pending = None
                filled = replace(
                    pending,
                    intent="log_transaction",
                    question_about=None,
                    amount=m.get("amount"),
                    amount_each=m.get("amount_each"),
                )
                return tools.log_transaction(self.ledger, filled, text)

        if pending.question_about == "item" and (pending.amount or pending.amount_each):
            words = [t for t in lowered
                     if t not in self.pack.fillers and not is_moneyish(t, self.pack)]
            if words and len(words) <= 4:
                self.pending = None
                filled = replace(
                    pending, intent="log_transaction", question_about=None,
                    item=" ".join(words),
                )
                return tools.log_transaction(self.ledger, filled, text)
        return None
