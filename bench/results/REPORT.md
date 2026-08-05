# SautiLedger ASR Benchmark Report

Corpus frozen before first run — manifest sha256: `d68d90443326f5abab5fcf84cc01841f1b3bd926def8703cfc59fb76ccd827a5`.
Clips scored: 55 (missing/skipped: 0).
> **Note:** No frontier API key was available; whisper-small substitutes as the third model. This is a weaker baseline than GPT-4o-transcribe/Gemini.

## Summary

### Corpus tier: `afriswitch-sample`

| Model | WER (norm) | WER (raw) | Numeric acc | Txn exact | Amount safe | **Amount corrupted** |
|---|---|---|---|---|---|---|
| sahara-v2 | 42.4% | 56.2% | – | – | – | **–** |
| whisper-large-v3 | 76.4% | 85.1% | – | – | – | **–** |
| whisper-small | 77.6% | 87.3% | – | – | – | **–** |

*(no parse ground truth in this tier: WER columns only)*

### Corpus tier: `sautiledger-clips`

| Model | WER (norm) | WER (raw) | Numeric acc | Txn exact | Amount safe | **Amount corrupted** |
|---|---|---|---|---|---|---|
| sahara-v2 | 71.6% | 80.8% | 53% | 40% | 80% | **20%** |
| whisper-large-v3 | 98.6% | 106.3% | 53% | 7% | 87% | **13%** |
| whisper-small | 119.4% | 120.0% | 53% | 7% | 93% | **7%** |

The three-level transaction metric is the point: WER alone understates the
differences for financial use. *Amount corrupted* counts transcripts that made
our normaliser log a WRONG amount — the failure a market trader cannot afford.
*Amount safe* includes clarify outcomes: an agent that asks is safe, an agent
that guesses is not. Transcription accuracy is necessary but not sufficient for
financial records; the grammar-first normaliser + clarify design is the safety
layer, and the amount-corrupted column is the evidence of what it repairs.

## Illustrative examples

**case01** — truth: `I don sell three derica of rice five thousand five`

- `sahara-v2`: `I don sell 3 karet of rice 5k 5.`
- `whisper-large-v3`: `I don't sell three Delica or Bryce 5005.`  ⚠ perfective_negation_inversion  ✗ AMOUNT CORRUPTED
- `whisper-small`: `I don't sell 3 Delica of Brice 5005`  ⚠ perfective_negation_inversion  ✗ AMOUNT CORRUPTED

**afx023** — truth: `kile kiwango kinachotakiwa cha kulipa dividends`

- `sahara-v2`: `Kile kiwango kinachotakiwa cha kulipa dividends?`
- `whisper-large-v3`: `If I don't have money, I won't be able to pay the dividend.`
- `whisper-small`: `Kila Kiwangu Kina Chotaki Wachabuli Padik, Edent.`

**case02** — truth: `sell one bag of beans forty five k`

- `sahara-v2`: `Sell one bag of beans for 45`
- `whisper-large-v3`: `Sell one bag of beans for $0.75`
- `whisper-small`: `Set 1, 4, 5, 6, 5, 6, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15.`

**afx016** — truth: `.... from the... Ikiwa tutaikomboa Mji wa Aleppo kutoka mkononi mwa magaidi`

- `sahara-v2`: `Aleppo kutoka kwa. Ikiwa tutaikomboa mji wa Aleppo kutoka mkononi mwa magaidi.`
- `whisper-large-v3`: `Aleppo from the...`
- `whisper-small`: `The repo from the key was to talk on bomb. You are a lepo. Could I come in on him? I'm a guy`

**afx019** — truth: `actually kwasababu hivi kwa mfano wa kitabu zitakazo nunuliwa, unajua hii nchi.`

- `sahara-v2`: `Actually, kwa sababu ni hivi, kwa mfano 500 zitakazonunuliwa, unajua hii ni nini.`
- `whisper-large-v3`: `Actually, because this is how it is. For example, 5 out of 5 people are not being bought. You know this country.`
- `whisper-small`: `Actually, because of the NIV. I'm going to put a little bit of my guitar in the middle of the song. I'm going to put it in the middle.`

## Per-model notes

**sahara-v2** — Built for exactly this speech: code-switched African utterances, dense numbers, market vocabulary. Cloud-only in this benchmark (offline deployment exists but was not under test); every call is visible in the egress ledger. Judged here on downstream safety, not just WER.

**whisper-large-v3** — Strong general-purpose local model; runs fully offline. Known weaknesses on Pidgin and Yoruba numerals; tends to 'anglicise' code-switched speech, which is precisely the error class that corrupts amounts downstream.

**whisper-small** — Lightweight local substitute (used only when no frontier API key was available). Fast and offline, but weakest on accented, code-switched speech — treat its numbers as a floor, not a fair frontier baseline.

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
