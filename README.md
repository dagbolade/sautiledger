# SautiLedger

**An offline-first, code-switched voice ledger for African market traders.**
Indaba 2026 · MLC (Africa) × Intron Agentic Voice AI Challenge.

A trader says *"I don sell three derica of rice five thousand five"* — Pidgin
grammar, Yoruba numerals, market units, money slang — and the agent logs
₦5,500 to a ledger that lives on her phone, reads the entry back for
confirmation, and answers *"abeg how much I don make today"* from local
SQLite. Her financial life never exists anywhere but her own device.

## The sovereignty design

Most voice agents ship your audio, your transcript, your conversation
history, and their own reasoning to someone's server. SautiLedger ships
**four seconds of audio** (to Sahara ASR) and nothing else. Two rules from
[CLAUDE.md](CLAUDE.md) make that a property of the code, not a promise:

1. **The only data that ever leaves the device is the audio clip sent for
   transcription.** The ledger, transcripts, parses, queries, and agent
   reasoning are local. `tests/test_import_guard.py` walks the AST of
   every module and fails the build if anything except `egress.py` can
   reach the network.
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
python -m pytest              # 58 tests, incl. the 20-case spec
python -m sautiledger.chat    # typed REPL (no mic needed)
python -m sautiledger.demo    # full UI at http://127.0.0.1:8090
```

(`make test` / `make chat` / `make demo` on machines with make.)
Copy `.env.example` to `.env` and add `SAHARA_API_KEY` for cloud ASR;
without it the app runs fully offline. The 90-second demo walkthrough is
in [demo/script.md](demo/script.md).

## Add your language in an afternoon

Language support is pure configuration — **no code changes** (enforced by
the acceptance rules in `normaliser_tests.json`):

1. Copy `packs/pcm-yo-NG.yaml` to `packs/<your-lang>.yaml`.
2. Fill in your number words, money slang, market units, and trigger
   phrases for sell/buy/query/correct/summary.
3. Add test cases with utterances in your own words to
   `normaliser_tests.json`.
4. `python -m pytest` until green.

The Swahili and Hausa packs here were drafted by a non-native speaker and
corrected with speakers at Indaba — that took about ten minutes per
language. Yours will too.

## Benchmark

`bench/` holds a standalone harness (required by the challenge) comparing
Sahara-v2, whisper-large-v3 (local), and a frontier API model across a
frozen corpus. Beyond WER, it measures what matters for money:

- **numeric accuracy** — did every amount survive transcription?
- **transaction accuracy** — feed each model's transcript through *our*
  normaliser: `exact_match` / `amount_safe` (correct **or** clarify —
  asking is safe) / **`amount_corrupted`** (a wrong amount would have
  been written — the number that must be ~0).

```
pip install -r bench/requirements.txt
python -m bench.run            # dry run: corpus + cost estimate
python -m bench.run --confirm  # transcribe (cached; reruns are free)
```

Report renders to `bench/results/REPORT.md` with the manifest hash frozen
before the first run. Sahara's failures, if any, are reported unedited —
the claim under test is downstream safety, not raw perfection.

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

- **Small grammar, by design.** The normaliser covers transaction speech,
  not open conversation. Out-of-grammar utterances get a clarify question
  (or the local LLM fallback, which is amount-guarded).
- **sw-KE and ha-NG packs are drafts** pending deeper native-speaker
  validation; the test file marks every case that needs it.
- **Voice out is browser speechSynthesis** — local and free, but
  robotic. Piper (nicer, still local) and Sahara TTS sit behind the same
  `TtsClient` interface; cloud TTS is deliberately not enabled because it
  would egress ledger contents (see `tts.py`).
- **Offline ASR is a stub** until Sahara's on-device engine is dropped
  into `SaharaOfflineAsr`. Offline mode today uses typed input / fixture
  audio — the rest of the stack is genuinely offline.
- **Single-user, single-device.** No sync, no backup, no auth. A trader's
  phone is the database; losing the phone loses the ledger.

## Licence

MIT. No API keys, personal data, or attendee voice recordings are in this
repo (venue recordings stay local; see `.gitignore`).
