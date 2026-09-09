# SautiLedger

**An offline-first, code-switched voice ledger for African market traders.**
Sahara CodeSwitch Africa Challenge (Phase 2) · category: Fintech.
Winner, Indaba 2026 MLC (Africa) × Intron workshop challenge.

**Live:** https://sautiledger-production.up.railway.app ·
**Submission docs:** [SOLUTION](submission/SOLUTION.md) ·
[ETHICS](submission/ETHICS.md) ·
[benchmark report](bench/results/REPORT.md) ·
[demo script](demo/script-phase2.md)

A trader says *"I don sell three derica of rice five thousand five"* — Pidgin
grammar, Yoruba numerals, market units, money slang — and the agent logs
₦5,500 to a ledger that lives on her own device when self-hosted (see
"Two deployment modes" below), reads the entry back for
confirmation, and answers *"abeg how much I don make today"* from local
SQLite. Her financial life never exists anywhere but her own device.

## The sovereignty design

Most voice agents ship your audio, your transcript, your conversation
history, and their own reasoning to someone's server. SautiLedger ships
**the audio clip** (to Sahara ASR) and, when the spoken readback is
enabled, **the reply sentence** (to Sahara TTS) — and nothing else, to
nobody else.

### Two deployment modes, and the difference matters

**Be precise about this, because the two are not the same:**

| | Where the ledger lives | What leaves it |
|---|---|---|
| **Self-hosted** (`make phone`, the intended production shape) | SQLite on the trader's own device | audio clip + reply text, to Sahara only |
| **Hosted demo** ([Railway](https://sautiledger-production.up.railway.app), what our field testers used) | SQLite on a server volume we operate | same — plus the utterance reaches our backend to get there |

The offline-first architecture is real and is what the self-hosted mode
does. **The hosted demo is not phone-local storage**, and we do not claim
it is: we run it so testers could use the app from a phone without
installing anything, which was the only way to get real market usage
inside the challenge window. Per-device cookies isolate each trader's
ledger from every other trader's; they do not move the storage onto the
phone. A trader running the hosted instance is trusting us as an operator,
exactly as they would any web app.

Two rules from [CONSTRAINTS.md](CONSTRAINTS.md) hold in **both** modes,
and are properties of the code rather than promises:

1. **Money records go to no third party.** The ledger, parses, queries and
   agent reasoning are never transmitted to any vendor or model; only the
   audio clip and the spoken reply text are, each one logged.
   `tests/test_import_guard.py` walks the AST of every module and fails
   the build if anything except `egress.py` can reach the network.
2. **Every transmission is logged** — timestamp, destination, purpose,
   bytes, disposition — to an egress ledger displayed at the top of the
   UI. Tap the meter, see everything the app has ever shared. In offline
   mode it reads **0.00 KB, in green**. With Sahara's offline deployment
   (`SaharaOfflineAsr` is the marked swap point), that line goes to zero
   for good.

And the money rule: **the agent never fabricates an amount.** Ambiguous
speech ("two two fifty" — ₦250 each or ₦2,250?) triggers a clarify
question, never a guess. A confident wrong entry in someone's money
records is the worst possible failure. The benchmark quantifies exactly
this (see below).

## Architecture

```
 phone browser                         FastAPI (localhost)
┌───────────────────┐                 ┌──────────────────────────────────┐
│ push-to-talk mic  │──audio/webm───▶│ POST /utterance                  │
│ chat bubbles      │◀──reply text───│   ├─ AsrClient                   │
│ ledger panel      │                 │   │   ├─ SaharaCloudAsr ─────┐  │
│ EGRESS METER      │                 │   │   ├─ SaharaOfflineAsr    │  │
│ speechSynthesis   │                 │   │   └─ FakeAsr (dev/tests) │  │
└───────────────────┘                 │   ├─ normaliser (grammar,    │  │
                                      │   │   packs/*.yaml, no LLM)  │  │
        the ONLY network path ────────┼───┼──▶ egress.py ────────────┘  │
        (logged to egress_log)        │   ├─ LLM fallback (Ollama,      │
                                      │   │   localhost, optional)      │
                                      │   ├─ agent → 4 tools            │
                                      │   └─ SQLite data/ledger.db      │
                                      └──────────────────────────────────┘
```

The normaliser is **deterministic and grammar-first**: intents, number
systems, money slang, and market units all come from declarative language
packs. A local 3B LLM (Ollama) is a fallback only for utterances the
grammar cannot read at all, and it is forbidden — by prompt *and* by a
validation layer that discards any number not literally present in the
utterance — from inventing amounts.

## Run it

```
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
python -m pytest              # full suite, incl. the 21-case corpus
python -m sautiledger.chat    # typed REPL (no mic needed)
python -m sautiledger.demo    # full UI at http://127.0.0.1:8090
python -m sautiledger.phone   # HTTPS on your LAN, for a phone's mic
```

(`make test` / `make chat` / `make demo` / `make phone` with make.)
Copy `.env.example` to `.env` and add `SAHARA_API_KEY` for cloud ASR;
without it the app runs fully offline. The 90-second demo walkthrough is
in [demo/script.md](demo/script.md); `python -m sautiledger.demo
--seed-demo` pre-loads two clearly-marked rows for screenshots.

## Add your language in an afternoon

Language support is pure configuration — **no code changes** (enforced by
the acceptance rules in `normaliser_tests.json`):

1. Copy `packs/pcm-yo-NG.yaml` to `packs/<your-lang>.yaml`.
2. Fill in your number words, money slang, market units, and trigger
   phrases for sell/buy/query/correct/summary.
3. Add test cases with utterances in your own words to
   `normaliser_tests.json`.
4. `python -m pytest` until green.

Four packs ship today, covering five languages plus English:

| Pack | Languages | Status |
|---|---|---|
| `pcm-yo-NG` | Nigerian Pidgin + Yoruba + English | native-validated, field-tested by real traders |
| `sh-ZW` | Shona + English (USD, cents) | native-validated — 15 utterances corrected *and* recorded by a native speaker, Sept 2026 |
| `sw-KE` | Swahili + English | grammar complete, native validation pending |
| `ha-NG` | Hausa + English | grammar complete, native validation pending |

Shona was added exactly this way and needed **no parser changes** — two
new grammar switches (`major_unit_words` for a cents-based currency,
`number_prefixes` for Bantu concord prefixes that glue onto code-switched
numerals, as in *"ne**five** dollars fifty"*) live in the pack and are
inert for every other language. Her corrections taught us things no
outsider would guess: `hwani` marks per-unit pricing, and traders quote
in US dollars spoken as *"two fifty"* for $2.50.

## Benchmark

`bench/` holds a standalone harness comparing **seven speech systems** —
Sahara v2.5, Microsoft MAI-Transcribe-2, OpenAI GPT-4o-transcribe, NVIDIA
Parakeet-TDT, Google Chirp-3, Whisper-large-v3 and Meta's omnilingual-ASR
(plus a frozen 5 August Sahara snapshot as a drift control) — across a
frozen 70-clip corpus of three tiers: natively recorded Pidgin/Yoruba
market speech, natively recorded Shona market speech, and AfriSwitch
broadcast code-switching. A separate round-trip harness benchmarks **TTS**
(`bench/tts_bench.py`). Beyond WER and CER, it measures what matters for
money:

- **numeric accuracy** — did every amount survive transcription?
- **transaction accuracy** — feed each model's transcript through *our*
  normaliser: `exact_match` / `amount_safe` (correct **or** clarify —
  asking is safe) / **`amount_corrupted`** (a wrong amount would have
  been written — the number that must be ~0).

```
pip install -r bench/requirements.txt
python -m bench.run                            # dry run: corpus + cost estimate
python -m bench.run --confirm --models sahara-v2.5   # one model at a time
python -m bench.run --score-only               # score every cached transcript, free
python -m bench.tts_bench --confirm            # TTS round-trip benchmark
```

Local models are memory-hungry, so each runs in its own pass and a final
`--score-only` pass assembles the report from cache.

Report renders to [`bench/results/REPORT.md`](bench/results/REPORT.md)
with the manifest hash frozen before the first run. Sahara's failures are
reported unedited — the claim under test is downstream safety, not raw
perfection.

**Headline result: no model wins everywhere, and the leader flips with the
language.** On Pidgin/Yoruba, Microsoft's MAI-Transcribe-2 records the
most transactions exactly (60%, zero corrupted) ahead of GPT-4o-transcribe
(53%) and Sahara (47%). On Shona the ordering inverts — Sahara leads at
27% with zero corrupted amounts, double the best frontier system, three of
which start corrupting amounts there. The pattern is linguistic distance
from English: Pidgin is lexically English-adjacent so general recognisers
cope, Shona is not and they collapse. An earlier draft of this benchmark,
run against a weaker field, concluded there was "one viable ASR"; a
stronger field falsified that, and the report says so.

The TTS round trip earned its keep immediately: it caught the app
**speaking its own punctuation** to the trader ("Logged expense**:** fuel"
came back as "Log the expense *call on*"), which was corrupting the amount.
Fixed and re-measured — hallucination 0.117 → 0.000, amount survival
91% → 100%.

## Changelog: post-benchmark product iterations

The benchmark (bench/results/REPORT.md) was frozen FIRST; these product
improvements came after measurement, from live phone testing — the
right order, and the numbers were not re-scored:

- **Narrated third-person sales**: "Blessing come my shop come buy
  biscuits for 50 naira" parses (narration prefix discarded — ASR
  mangles names); a narrated sale with the money tail lost by ASR asks
  the amount question a fellow trader would ask, not a generic prompt.
- **Widened LLM fallback**: long utterances (>6 words) with a sale
  signal the grammar can't complete get one local-3B structured-
  extraction attempt — same iron rule: an amount must be literally
  present in the transcript or it becomes a clarify.
- **Conversational confirmation**: "yes, and then…" confirms and
  processes the rest in one breath; bare "no" opens the correction flow.
- **Ledger row polish + void**: clean "item ×qty" display and a ✕ per
  row — deletion is a soft void (row persists in the DB marked voided,
  logged, never silent).

See [ROADMAP.md](ROADMAP.md) for what was found and deliberately not
built during the freeze.

## Honest limitations

- **Conversational-speed ASR fidelity.** Command-style utterances
  transcribe well; fast narrated speech degrades — the benchmark's tier-a
  numbers quantify this, and the clarify design absorbs most of it.
- **The two deletion-class corruptions the workshop report admitted are
  now closed.** A confidence-weighted readback echoes the full amount
  before committing whenever the shape of a number suggests a dropped
  word ("[ten] thousand" arriving as a bare "thousand") or a swallowed
  correction cue. Calibrated on the exact failing clips, with zero added
  friction on legitimate short amounts.
- **Tier-a benchmark audio is a single speaker** (the developer) —
  directional, not population-level, evidence.
- **Small grammar, by design.** The normaliser covers transaction speech,
  not open conversation. Out-of-grammar utterances get a clarify question
  (or the local LLM fallback, which is amount-guarded).
- **sw-KE and ha-NG packs are drafts** pending deeper native-speaker
  validation; the test file marks every case that needs it.
- **Voice out is Sahara TTS** in a Nigerian Pidgin voice
  (`voice_language=pcm`, `voice_accent=pidgin`), routed through the egress
  ledger like everything else and cached by phrase so repeated
  confirmations cost nothing. Browser `speechSynthesis` remains the
  offline fallback; Piper sits behind the same `TtsClient` interface.
  Sending the reply text is a real disclosure and is logged as one.
- **Offline ASR is a stub** until Sahara's on-device engine is dropped
  into `SaharaOfflineAsr`. Offline mode today uses typed input / fixture
  audio — the rest of the stack is genuinely offline.
- **One trader per device, and no account.** Each device gets its own
  isolated ledger (a `sauti_device` cookie), so several traders can use
  the same deployment without ever seeing each other's books — but there
  is no sync, no backup and no login. Losing the device loses the ledger.
- **One language pack per deployment.** The live instance runs
  `pcm-yo-NG`; the other packs are selected with `SAUTI_PACK` at start-up
  rather than by the user at runtime.
- **The agent understands four languages but answers in one.** Packs
  drive *parsing*; the reply templates ("Logged: …, five thousand five
  hundred naira. Correct?") are still Pidgin/English strings. Run the
  Shona pack and it will parse `Ndatengesa matomatisi ethree dollars`
  correctly, do the arithmetic in dollars and cents, and then answer in
  Pidgin. Moving the reply strings into the pack is the obvious next
  step; we have not done it, and would rather say so than imply a
  finished multilingual UX.

## Built with, and thanks

- **Intron Sahara v2.5** (infer.voice.intron.io) — ASR (sync and
  streaming) and TTS, the only network calls this app makes, and the
  reason code-switched market speech transcribes at all.
- **AfriSwitch** (huggingface.co/datasets/intronhealth/AfriSwitch,
  CC BY-NC-SA 4.0) — used for evaluation only, fetched at run time,
  never redistributed, and not used to train or build the product.
- Local pieces: FastAPI, PyAV, faster-whisper and Meta omnilingual-ASR
  (benchmark only), Ollama + Llama 3.2 3B (optional local fallback),
  browser speechSynthesis (offline voice fallback).
- Built during Deep Learning Indaba 2026 with AI-assisted development;
  all language corrections and design decisions came from a
  native-speaker human in the loop.

## Licence

MIT. No API keys, personal data, or attendee voice recordings are in this
repo (venue recordings stay local; see `.gitignore`).
