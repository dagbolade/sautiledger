# SautiLedger ASR Benchmark Report

Corpus frozen before first run — manifest sha256: `9c183263845c0c52b0b5764c87b4afc059d7282cfcea1944efc6a99f2138ae67`.
Clips scored: 20 (missing/skipped: 0).
> **Note:** DRY RUN: all three models are FAKE text transforms of the ground truth (echo / anglicised / amount-mangler). Numbers are illustrative of the table structure only.

## Summary

### Corpus tier: `sautiledger-clips`

| Model | WER (norm) | WER (raw) | Numeric acc | Txn exact | Amount safe | **Amount corrupted** |
|---|---|---|---|---|---|---|
| FAKE-anglicised | 13.8% | 13.8% | 95% | 80% | 100% | **0%** |
| FAKE-echo | 0.0% | 0.0% | 100% | 100% | 100% | **0%** |
| FAKE-mangler | 5.7% | 5.7% | 70% | 65% | 70% | **30%** |

The three-level transaction metric is the point: WER alone understates the
differences for financial use. *Amount corrupted* counts transcripts that made
our normaliser log a WRONG amount — the failure a market trader cannot afford.
*Amount safe* includes clarify outcomes: an agent that asks is safe, an agent
that guesses is not. Transcription accuracy is necessary but not sufficient for
financial records; the grammar-first normaliser + clarify design is the safety
layer, and the amount-corrupted column is the evidence of what it repairs.

## Illustrative examples

**case01** — truth: `I don sell three derica of rice five k five`

- `FAKE-anglicised`: `I don't sell three derica of rice 5.5k`  ⚠ perfective_negation_inversion
- `FAKE-echo`: `I don sell three derica of rice five k five`
- `FAKE-mangler`: `I don sell three derica of rice five k`  ✗ AMOUNT CORRUPTED

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

**case10** — truth: `no no na five k not five k five`

- `FAKE-anglicised`: `no no na five k not 5.5k`
- `FAKE-echo`: `no no na five k not five k five`
- `FAKE-mangler`: `no no na five k not five k`

## Per-model notes

**FAKE-anglicised** — No notes.

**FAKE-echo** — No notes.

**FAKE-mangler** — No notes.

## Methodology & caveats

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
