# SautiLedger — Solution Description

**Sahara CodeSwitch Africa Challenge (Phase 2) · Category: Fintech, Telco & Customer Experience**

## The problem

A market trader in Lagos sells forty times a morning. Her hands are full,
her customers are waiting, and her record of the day lives in her head
until it doesn't. When a lender later asks "what does this business
earn?", there is nothing to show — not because the business is small, but
because nobody built a book she could keep while trading.

Typing is the wrong interface: it needs a free hand, a still moment, and a
keyboard that assumes English. Voice is the right interface — but voice
tools fail her twice over. They don't understand Nigerian Pidgin, and they
break at exactly the moment she mixes languages, which is every sentence:
*"I don sell three derica of rice five thousand five."* One utterance,
three languages, one price, and no mainstream ASR renders it correctly.

The gap is measurable and, until now, unmeasured. Microsoft's PazaBench —
the leading ASR leaderboard for low-resource languages — covers 61 African
languages across 53 models. **Nigerian Pidgin is not among them.** The
dominant contact language of West African commerce is absent from the
scoreboard.

## Target users

Traders in informal commerce: the market stalls, kiosks and roadside
businesses that make up the majority of African economic activity and the
minority of its recorded transactions. Concretely, this build has been
used by real egg and provisions traders in Nigeria, and its language packs
cover:

| Pack | Languages | Validation |
|---|---|---|
| `pcm-yo-NG` | Nigerian Pidgin + Yoruba + English | native-validated, field-tested |
| `sh-ZW` | Shona + English (USD) | native-validated (recorded 7 Sep) |
| `sw-KE` | Swahili + English | grammar complete, native validation pending |
| `ha-NG` | Hausa + English | grammar complete, native validation pending |

We label the last two honestly as unvalidated rather than claiming four
finished languages.

## The solution

SautiLedger is an agentic voice bookkeeper. The trader talks; the book
writes itself.

```
speech ─▶ Sahara STT ─▶ grammar-first normaliser ─▶ [SAFETY GATE] ─▶ ledger
                                │                        │
                          (clarify if unsure)      spoken readback
                                                   via Sahara TTS
```

The voice input drives real downstream actions, not transcription for its
own sake:

- **Log** sales, expenses and credit, with quantity, unit, item and price.
- **Answer** questions against the ledger — *"wetin remain?"* returns real
  arithmetic over real rows, not a guess.
- **Correct** entries by voice — *"no, na ten thousand"* voids and replaces.
- **Summarise** the day, and **export a bank-readiness statement**: totals,
  net position, average daily revenue, a days-active consistency line, and
  a disclaimer stating plainly that it is transaction history, not a credit
  assessment.

## Key technical decisions

**1. Grammar first; the LLM is a guarded fallback.** Money is parsed by a
deterministic, pack-driven grammar. An LLM is consulted only when the
grammar has no reading at all, and its output is discarded if it contains
any amount not literally present in the utterance. The invariant is
absolute: **never fabricate an amount.**

**2. Clarify over guess.** Where meaning is genuinely ambiguous, the agent
asks. A ledger that asks is safe; a ledger that guesses is a liability.
This is why our benchmark scores *amount safe* (correct **or** asked)
separately from *transaction exact*.

**3. One gate in front of every write.** A single `_gate_and_commit` path
guards every commit: garbled items are refused outright, unknown items are
confirmed, and strangely-shaped amounts are verified once before writing.
This exists because of a real incident — on 27 August a live user's spoken
"5700" was transcribed as "570007" and reached the ledger. The gate now
closes that class of failure everywhere, and the flawed row remains in her
book, voided, as an audit trail.

**4. Languages are data, not code.** A language pack is a YAML file:
numbers, units, connectives, triggers, grammar switches. Adding Shona
meant adding a file and a test corpus — no parser changes. Two grammar
switches added for Shona (`major_unit_words` for cents-based currency,
`number_prefixes` for concord prefixes that glue onto code-switched
numerals) are pack-gated and provably inert for every other language.

**5. Egress is auditable by construction.** Exactly one module may touch
the network, enforced by an AST import guard in the test suite. Every
transmission — every clip, every TTS request, every streamed byte — is
recorded and shown to the user in plain language. The money records
themselves never leave the device.

**6. Offline-first.** The ledger is local SQLite. Cloud ASR is the
accuracy path, not a dependency of record-keeping.

## Evidence it works

- **Deployed and used by real traders**, not a demo reel: production at
  `sautiledger-production.up.railway.app`, per-device sessions, field
  instrumentation with consented retention.
- **The safety layer caught a real corruption in production** and the
  voided row is visible in the ledger as evidence.
- **Field findings became fixes**, twice: price connectives and a typed
  shorthand register in round one; the wholesale register (`per pack`,
  `200 per one`) in round two, taken directly from a trader's transcripts.
- **Benchmarked against five ASR systems** on a frozen corpus of natively
  recorded code-switched market speech — see `bench/results/REPORT.md`.

## Prior work

This is the continuation of our winning entry in the Indaba 2026 workshop
challenge (Intron's "Built with Sahara" showcase). The workshop benchmark
report is preserved in this repository as
`bench/results/REPORT-workshop-2026-08.md` and cited as prior work; every
number in the Phase 2 report is a fresh measurement.
