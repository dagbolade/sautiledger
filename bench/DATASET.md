# SautiLedger Market-Speech Benchmark: dataset card

A benchmark for **voice bookkeeping in code-switched African market
speech**. Most ASR test sets can tell you whether the words came out
right. This one also tells you whether **the money** came out right: each
native clip is labelled with the ledger entry it should produce, so a
speech system is judged on whether a trader's sale would have been
recorded correctly, refused safely, or written down wrong.

Results on this dataset: [`results/REPORT.md`](results/REPORT.md).

## At a glance

| Tier | Directory | Clips | Audio | Languages | Speakers | Ground truth |
|---|---|---|---|---|---|---|
| **tier-a** | `corpus/sautiledger-clips/` | 15 | 1.1 min | Nigerian Pidgin + Yoruba + English | 1 (Nigerian, male) | transcript **+ transaction label** |
| **tier-sh** | `corpus/sh-clips/` | 15 | 1.2 min | Shona + English, prices in USD | 1 (Zimbabwean, female) | transcript **+ transaction label** |
| **tier-b** | `corpus/afriswitch-sample/` | 40 | 8.2 min | Pidgin 16 · Swahili 12 · Yoruba 6 · Hausa 6 (each with English) | many (broadcast) | transcript only |
| **yo-farm** (supplementary) | `corpus-supplementary/yo-farm/` | 15 | 1.3 min | Yoruba + English, farm trading | 1 (Nigerian, female) | script + transaction label (2 labels flagged) |
| **conversations** | `conversation_scenarios.json` | 37 scenarios | text | Pidgin/Yoruba/English, Shona/English | - | final ledger state, expected replies |

**Frozen corpus hash (manifests):**
`50e5e064312fd6bfe05c5aad6662be75f2b31e1525f57917d403849dd4377aeb`.
This is the sha256 over the three `manifest.jsonl` files, read in sorted
directory order. It was fixed before the first model was run, and no clip
has been added, dropped or relabelled since. To recompute it once the
corpus is in place:

```
python -c "from bench.run import load_corpus; print(load_corpus()[1])"
```

Each manifest's own sha256, so a single tier can be checked alone:

| Manifest | sha256 | In repository |
|---|---|---|
| `afriswitch-sample/manifest.jsonl` | `b0684132931992cf8923b4e665163d4bee5382629056bfdbcac85d8817fd40e3` | no (AfriSwitch text, see below) |
| `sautiledger-clips/manifest.jsonl` | `93cde7ee0afa5dd6f7b45c845e9d04897719490a99c9b235a1c5a2c01ce568d0` | yes |
| `sh-clips/manifest.jsonl` | `b7625f28a85f5d3b352dab5d9e9cf069cf47a32a3a90ea0b3ede31ddbafc415b` | yes |

**Supplementary tier (14 September).** `yo-farm` was recorded after all
frozen results were fixed and sits outside `bench/corpus/`, so it does not
change the frozen hash; it has its own manifest sha256, printed by
`python -m bench.supplementary --score-only`. The speaker was invited to adapt
the wording, so references are the script; two clips (`yo04`, `yo10`) carry a
different spoken price and are marked `label_uncertain` in the manifest.

## What makes it different

1. **Transaction labels, not just transcripts.** Every tier-a and tier-sh
   clip carries an `expected_parse`: intent, sale or expense, item,
   quantity, unit, amount and currency. Amounts are stored in the currency's
   storage unit (naira; US **cents** for Shona, because Zimbabwean traders
   say *"two fifty"* for $2.50). This supports three scores that WER
   cannot give: **transaction exact**, **amount safe** (right, or the
   system asked instead of guessing) and **amount corrupted** (a wrong
   number would have entered someone's money records).
2. **"Ask" is sometimes the correct answer.** Some clips are labelled
   `clarify`. *"Ndatengesa chibage chese"* ("I sold all the maize") names
   no price, so the right behaviour is a question, not an entry. Intents
   across the 30 native clips: 15 transactions, 5 clarifications,
   4 ledger queries, 4 corrections, 2 daily summaries.
3. **Written by native speakers, not machine-translated.** Utterances were
   drafted, then **corrected by a native speaker before recording**. The
   Shona corrections are how we learnt `hwani` ("each"), and that Shona
   glues concord prefixes onto English numbers (*"ne**five** dollars"*).
   Those forms are what real traders say, and a translated test set
   would not contain them.
4. **The ledger has to stay empty on chatter.** 17 conversation scenarios
   replay real, unscripted Shona market talk (greetings, *"your tomatoes
   aren't fresh"*, *"won't you give me a little extra?"*). They are
   replayed as Sahara v2.5's own transcripts, errors included, and pass
   only if **nothing** is written to the ledger.

## How it was built

- **Recording.** Each native tier was recorded by one speaker on their own
  phone in their own room, then converted to 16 kHz mono 16-bit PCM WAV
  (`convert_clips.py`). Quality gates: 1-15 s long, readable, not silent.
- **tier-a** was recorded in August for our workshop entry. The manifest
  lists 21 cases; cases 14-19 were never recorded and are left out of
  every score rather than silently dropped.
- **tier-sh** was recorded on 7 September. The speaker's files arrived
  numbered "Ruwa 2-16"; we matched them to script cases 1-15 by content,
  using a local model, and checked the order.
- **tier-b** is the first *N* rows of the AfriSwitch `test` split for each
  language, in stream order with no filtering by result
  (`fetch_afriswitch.py`). The per-clip code-mixing index and switch counts
  are copied from the source as fetched on 3 August. AfriSwitch was
  republished on 7 September, so a re-fetch today may return different
  rows. Compare the manifest's sha256 above: if it differs, the tier-b
  numbers are not comparable with ours.
- **Conversations.** 11 written by us, 4 taken verbatim from a field
  tester's typed session, 5 taken verbatim from Sahara transcripts of real
  spoken sessions, and 17 of real Shona chatter (above). Scenarios whose
  correct outcome is *not* completing are scored as controls, separately.

## Known limitations

- **Small.** 15 clips on each native tier, so a single clip moves a
  percentage by almost 7 points.
- **One speaker per native tier.** Language is confounded with voice,
  microphone and room, so no comparison between tiers isolates language.
- **tier-b has no transaction labels.** Broadcast speech is not
  bookkeeping, so it is scored on WER and CER only.
- **Swahili and Hausa** appear only in tier-b. Our own Swahili and Hausa
  cases were written by non-native speakers and are not included.
- **The Shona chatter transcripts are unverified.** They are what Sahara
  heard, not what was said. That is why they are used only where the
  expected outcome (an empty ledger) does not depend on the words, and
  never for WER.
- **tier-a references are the script, not a verbatim record.** In 4 of
  15 clips (case09, case12, case13, case21) the speaker added openers such
  as *"How far na"* or *"My guy"* that the reference does not contain. This
  inflates tier-a WER for every model (Sahara v2.5: 0.574 with them,
  0.358 without; the ranking barely moves). Transaction labels are
  unaffected. The published audio set carries both the script and a
  speaker-confirmed verbatim transcript.
- **Speech was read, not overheard.** Native-tier clips are scripted
  utterances spoken naturally, not recordings of live trade.

## Access and licence

- **Manifests and labels** we wrote (tier-a, tier-sh, conversations) are
  covered by the repository's MIT licence.
- **tier-b** comes from
  [intronhealth/AfriSwitch](https://huggingface.co/datasets/intronhealth/AfriSwitch)
  (CC BY-NC-SA 4.0, gated). We redistribute neither its audio nor its
  transcripts. `python -m bench.fetch_afriswitch --confirm` rebuilds the
  tier from the source after you accept its terms.
- **Native-tier audio is not in the repository**, but both native tiers
  (30 clips) are published on Hugging Face, each with its speaker's
  explicit consent to public release given on 13 September 2026, as
  16 kHz WAV with transcripts, durations and ledger labels. Voices from
  other app testers are not included: the in-app consent covers testing
  inside the app, not publication (see `submission/ETHICS.md` §2).
- **Scores can be checked without any audio.** `results/metrics.json`
  holds every model's per-clip transcript and score for tier-a and
  tier-sh. For tier-b, where the transcripts are AfriSwitch's text, it
  holds the scores only.

## Using it

```
pip install -r bench/requirements.txt
python -m bench.run                  # dry run: corpus check + hash + cost
python -m bench.run --score-only     # rebuild every score from cached transcripts
python -m bench.conversations        # replay the conversation scenarios
python -m bench.report_g             # regenerate results/REPORT.md
```

To score a new ASR system, add an adapter with
`transcribe_file(path, language_hint) -> str` in `bench_asr.py`. Its
transcripts are cached per clip, so scoring can be repeated for free.
