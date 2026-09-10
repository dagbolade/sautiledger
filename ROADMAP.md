# Roadmap — beyond the hackathon freeze

Discovered during live testing and benchmarking; deliberately NOT built
during the submission window (scope discipline > feature count).

- **Confidence-weighted readback.** The benchmark's two residual
  corruption cases are ASR word *deletions* ("ten thousand" → "thousand";
  "no no" → "no") that no deterministic guard catches. Fix direction:
  when ASR confidence on numeral tokens is low, the readback spells out
  the full amount and requires an explicit yes before commit.
- **Customer-name capture.** Narrated sales ("Blessing come buy…")
  currently discard the narration prefix. Storing a best-effort customer
  note would enable per-customer credit tracking — the feature traders
  ask for first.
- **Multi-item utterances.** "I sell garri 500 and beans 300" logs only
  one entry today; a segmentation pass could split compound sales.
- **Sahara offline engine.** `SaharaOfflineAsr` is the marked swap
  point; when Intron ships the on-device model, offline mode gains real
  voice and the egress meter goes to zero for good.
- **Deeper sw-KE / ha-NG validation.** Venue-corrected, but each pack
  deserves the same native-speaker grammar treatment pcm-yo-NG got
  (reduplication rules, narrated forms, money idioms).
- **Correction of arbitrary entries.** `correct_last_entry` only touches
  the last row; "that garri from morning na credit" needs entry
  addressing by item + time.

## Credit needs a debtor (found in the field, 10 September 2026)

**The gap.** Credit itself works: a sale can be marked `credit`, a due
date is captured ("she go pay on Friday"), and `who dey owe me` returns
the outstanding total. What is missing is *who owes it*. The transactions
table has no customer column, so a buyer's name — when a trader says one
— is discarded, surviving only inside `raw_utterance`, which nothing
queries.

**Why that matters more than it sounds.** A credit book without names is
not a credit book. If six people buy on credit in a morning, "Credit
outstanding: ₦12,000" is not actionable — the trader cannot go and
collect, and chasing debts is a large part of why market traders keep
books at all. It also weakens the statement export: a lender reading
"credit outstanding" with no debtor list is being shown a number they
cannot verify.

**How traders actually say it** (real examples, both observed):
- name first — *"iya emma come my shop take 2 eggs worth 500 naira each
  she no pay"*
- name in the middle — *"I sell 2 carton of indomie **for yaboki** for
  5000 naira"*

Note the second is a live voice transcript from a deployed-app tester, so
this is not hypothetical phrasing.

**Design.**
1. `customer TEXT` column on `transactions`, added by the existing
   in-place migration (nullable; every existing row stays valid).
2. Capture the name at parse time, in the pack rather than the parser:
   a `buyer_markers` list (`for`, `come my shop`, …) and the same
   discard-the-prefix treatment narrated sales already use.
3. `credit_outstanding` returns rows, not a total: who, what, how much,
   due when.
4. Statement export gains a debtor table under the credit line.

**Why it is not in the submission build.** Adding the column is trivial;
teaching the parser to capture names is not. Names are unbounded free
text arriving mangled from ASR, and they sit directly beside the money —
that is precisely the code path that produced the two worst defects this
project has had (a ₦570,007 garbled item, and a row literally named
"yes"). Shipping that four days before a one-shot submission deadline,
onto a deployment that real testers were using that week, was a bad
trade: a missing feature costs a roadmap line, a corrupted ledger costs
the thing the product is for.

**One consequence worth fixing sooner.** The current reply when a buyer's
name appears is *"repeat the sale … without the buyer's name"*. That asks
the trader to discard the field she most needs, and it sits awkwardly
beside the claim in ETHICS.md that the app does not ask her to talk
differently so the machine can cope. Until names are captured, a softer
reply that logs the sale and simply drops the name is the better
behaviour.
