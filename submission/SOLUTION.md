# SautiLedger — Solution Description

**Sahara CodeSwitch Africa Challenge (Phase 2) · Category: Fintech, Telco & Call Center**

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

**5. Egress is auditable.** On the hosted demo, SAUTI_AGENT=hosted is enabled: utterance text the grammar cannot parse may be sent to the Hugging Face inference router (router.huggingface.co). Each call is listed as "agent fallback (hosted model)" in the in-app transmission list. Self-hosted setups can disable remote fallback with SAUTI_AGENT=none or use auto for local Ollama only. Audio is sent to Sahara for transcription; reply text is sent for online TTS. These texts and audio can contain transaction details. The ledger database itself is not uploaded to these services.

**6. Storage follows the backend.** SQLite lives on the machine running Python, or on the Railway server volume for the hosted demo. `make phone` serves a browser on the LAN; it does not put SQLite on the phone. Hosted use requires internet. The grammar and ledger can run without cloud inference in self-hosted none/auto mode.

## Evidence it works

- **Deployed and used by real traders**, not a demo reel: production at
  `sautiledger-production.up.railway.app`, per-device sessions, field
  instrumentation with consented retention.
- **The safety layer caught a real corruption in production** and the
  voided row is visible in the ledger as evidence.
- **Field findings became fixes**, twice: price connectives and a typed
  shorthand register in round one; the wholesale register (`per pack`,
  `200 per one`) in round two, taken directly from a trader's transcripts.
- **Benchmarked against six other speech systems** on a frozen 70-clip
  corpus: 30 natively recorded code-switched market utterances
  (Pidgin/Yoruba and Shona, each labelled with the ledger entry it should
  produce) and 40 AfriSwitch broadcast clips — Sahara v2.5,
  Microsoft MAI-Transcribe-2, OpenAI GPT-4o-transcribe, NVIDIA
  Parakeet-TDT, Google Chirp-3, Whisper-large-v3 and Meta's
  omnilingual-ASR — plus a round-trip TTS benchmark. Full results:
  [`bench/results/REPORT.md`](../bench/results/REPORT.md); dataset card:
  [`bench/DATASET.md`](../bench/DATASET.md).
- **Conversation benchmark**: 37 scripted replays through the real agent
  and ledger — 16 of 19 tasks completed, none ending with a wrong amount,
  and 18 of 18 must-not-log controls held, 17 of them real unscripted
  Shona market chatter.

### What the benchmark told us, including the inconvenient part

Measured on transactions actually recorded correctly, **no single model
wins, and in our sample the leader flips with the language**. With 15
clips per language these transaction gaps are *not* statistically
significant (MAI and Sahara differ on only 4 Pidgin clips, p = 0.63), so we
report them as a direction, not a ranking. What is significant is
transcription quality on Shona: Sahara's WER is lower than GPT-4o, Parakeet,
Chirp-3 and Whisper at p < 0.05.

| | Pidgin/Yoruba | Shona |
|---|---|---|
| best | MAI-Transcribe-2 — 60% exact, 0% corrupted | **Sahara v2.5 and Meta omnilingual-ASR (open), tied — 27% exact, 0% corrupted** |
| Sahara | 47% exact, 0% corrupted (3rd) | tied first, double the best frontier model |
| frontier models on Shona | — | 7–13% exact, three of them corrupting amounts |

Sahara is **not** the strongest system on its own flagship Pidgin/Yoruba
pair, and we report that plainly. Our best explanation — a hypothesis, since
each tier is one speaker on one phone — is linguistic distance from
English: Pidgin is lexically English-adjacent so strong general
recognisers cope with it, while Shona is not and they collapse there. If
that holds, code-switch-specific training is worth most exactly where
general models are worst.

**Why the product still runs on Sahara.** It has the best WER on every
tier; it is tied first on Shona with zero corrupted amounts, while the
open model it ties with records far fewer Pidgin transactions exactly
(13% against Sahara's 47%); it renders
Pidgin's perfective `I don sell` without inverting it into `I don't
sell`; and it is the only vendor here that also provides TTS in the same
Nigerian voice register, which our readback depends on. The honest
engineering conclusion is that a production deployment should **route by
language** — and the benchmark is what tells us that, which is the point
of running one properly rather than as a formality.

## Prior work

This is the continuation of our winning entry in the Indaba 2026 workshop
challenge (Intron's "Built with Sahara" showcase). The workshop benchmark
report is preserved in this repository as
`bench/results/REPORT-workshop-2026-08.md` and cited as prior work; every
number in the Phase 2 report is a fresh measurement.
