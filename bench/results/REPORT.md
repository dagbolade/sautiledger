# SautiLedger ASR Benchmark Report

Corpus frozen before first run — manifest sha256: `d68d90443326f5abab5fcf84cc01841f1b3bd926def8703cfc59fb76ccd827a5`.
Clips scored: 61 (missing/skipped: 0).
> **Note:** DRY RUN: all three models are FAKE text transforms of the ground truth (echo / anglicised / amount-mangler). Numbers are illustrative of the table structure only.

## Summary

### Corpus tier: `afriswitch-sample`

| Model | WER (norm) | WER (raw) | Numeric acc | Txn exact | Amount safe | **Amount corrupted** |
|---|---|---|---|---|---|---|
| FAKE-anglicised | 0.3% | 0.3% | – | – | – | **–** |
| FAKE-echo | 0.0% | 0.0% | – | – | – | **–** |
| FAKE-mangler | 0.0% | 0.0% | – | – | – | **–** |

*(no parse ground truth in this tier: WER columns only)*

### Corpus tier: `sautiledger-clips`

| Model | WER (norm) | WER (raw) | Numeric acc | Txn exact | Amount safe | **Amount corrupted** |
|---|---|---|---|---|---|---|
| FAKE-anglicised | 14.1% | 14.1% | 95% | 81% | 100% | **0%** |
| FAKE-echo | 0.0% | 0.0% | 100% | 100% | 100% | **0%** |
| FAKE-mangler | 5.4% | 5.4% | 71% | 67% | 71% | **29%** |

The three-level transaction metric is the point: WER alone understates the
differences for financial use. *Amount corrupted* counts transcripts that made
our normaliser log a WRONG amount — the failure a market trader cannot afford.
*Amount safe* includes clarify outcomes: an agent that asks is safe, an agent
that guesses is not. Transcription accuracy is necessary but not sufficient for
financial records; the grammar-first normaliser + clarify design is the safety
layer, and the amount-corrupted column is the evidence of what it repairs.

## Illustrative examples

**case01** — truth: `I don sell three derica of rice five thousand five`

- `FAKE-anglicised`: `I don't sell three derica of rice 5.5k`  ⚠ perfective_negation_inversion
- `FAKE-echo`: `I don sell three derica of rice five thousand five`
- `FAKE-mangler`: `I don sell three derica of rice five thousand`  ✗ AMOUNT CORRUPTED

**case21** — truth: `I don sell garri finish`

- `FAKE-anglicised`: `I don't sell garri finish`  ⚠ perfective_negation_inversion
- `FAKE-echo`: `I don sell garri finish`
- `FAKE-mangler`: `I don sell garri finish`

**case05** — truth: `sell garri egberun meta`

- `FAKE-anglicised`: `sell garri a thousand meters`
- `FAKE-echo`: `sell garri egberun meta`
- `FAKE-mangler`: `sell garri egberun`  ✗ AMOUNT CORRUPTED

**case02** — truth: `sell one bag of beans forty five k`

- `FAKE-anglicised`: `sell one bag of beans 45k`
- `FAKE-echo`: `sell one bag of beans forty five k`
- `FAKE-mangler`: `sell one bag of beans forty five k`

**case09** — truth: `wetin I sell pass this week`

- `FAKE-anglicised`: `what in I sell pass this week`
- `FAKE-echo`: `wetin I sell pass this week`
- `FAKE-mangler`: `wetin I sell pass this week`

## Per-model notes

**FAKE-anglicised** — No notes.

**FAKE-echo** — No notes.

**FAKE-mangler** — No notes.

### The reduplication finding

Case 4 ("two two fifty") was originally specced as an ambiguity requiring
a clarify question. Native-speaker review corrected this: in Nigerian Pidgin,
reduplicated money **is** the distributive — 250 each, unambiguously. An
outsider (and the AI that drafted the corpus) hears ambiguity where native
grammar encodes meaning. The parse rule now lives in the pcm-yo-NG pack,
gated off for packs that have not had native validation.

## Methodology & caveats

- Provenance: tier-a utterances were drafted by an AI assistant and CORRECTED
  by a native Nigerian Pidgin/Yoruba speaker before recording; sw-KE and ha-NG
  cases remain non-native drafts pending venue validation (flagged per-case).
  Even the test corpus required native-speaker repair — the same gap the
  product exists to close.
- Licence: AfriSwitch (CC BY-NC-SA 4.0) is used for evaluation only, never
  redistributed, and not used to train or build the product.
- WER: word-level (S+D+I)/N. Normalised = lowercase, punctuation stripped,
  whitespace collapsed (jiwer-standard). The Intron-Multimodal-Benchmarking
  repo reports normalised + unnormalised WER but does not publish its
  normaliser; ours is stated here so numbers are interpretable, not claimed
  identical to theirs.
- Numeric accuracy: every expected amount/quantity must be recoverable from
  the transcript after format normalisation ('5.5k' == 'five k five' == 5500).
- Transaction accuracy: each raw transcript is fed through the SautiLedger
  grammar-first normaliser (LLM fallback disabled) and compared to the
  expected ParseResult.
- Caveats: small n; tier `sautiledger-clips` is a single speaker (the
  developer); sw-KE/ha-NG ground truths drafted non-natively pending venue
  validation. Sahara failures, where they occur, are reported unedited —
  the claim under test is downstream safety, not raw perfection.
- Citations: **AfriSwitch** (huggingface.co/datasets/intronhealth/AfriSwitch,
  licence CC BY-NC-SA 4.0; 54.41h / 16,602 code-switched utterances across
  14 African languages paired with English; used here for non-commercial
  benchmarking, samples fetched at run time and never redistributed);
  AfriVox / AfriSpeech datasets © Intron Health; Olatunji et al.,
  *AfriSpeech-200: Pan-African Accented Speech Dataset for Clinical and
  General Domain ASR* (TACL 2023);
  github.com/intron-innovation/Intron-Multimodal-Benchmarking.
