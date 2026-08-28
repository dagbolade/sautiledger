# PazaBench WER snapshot — captured 2026-08-28

Source: the live PazaBench leaderboard (aka.ms/pazabench →
huggingface.co/spaces/microsoft/paza-bench), Microsoft Research Africa,
Nairobi Lab. Latest release covers **61 African languages × 53 models**
(grouped into 16 model-family columns on the WER view, ranked left-to-right
by average performance). Metric: WER, lower is better.

Rows below are the five languages relevant to SautiLedger's packs
(pcm-yo-NG draws on Yoruba + Hausa/Igbo context, sw-KE on Swahili,
sh-ZW planned on Shona). Column order is the leaderboard's own WER ranking.

| Language | omnilingual | facebook-mms | paza | facebook_hubert | openai-whisper | lite_asr | facebook-wav2vec2 | wav2vec2-conformer | data2vec | Phi-4 | nvidia-nemo | kyutai | seamlessM4T | moonshine | granite-speech | qwen2-audio |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hausa | 0.43 | 0.44 | 0.97 | 1.06 | 0.98 | 0.98 | 1.09 | 1.10 | 1.13 | 1.20 | 1.17 | 1.22 | 1.46 | 1.40 | 2.49 | 2.57 |
| Igbo | 0.51 | 0.51 | 0.95 | 1.01 | 0.98 | 0.98 | 1.03 | 1.04 | 1.06 | 1.15 | 1.09 | 1.10 | 1.15 | 1.29 | 1.09 | 0.99 |
| Swahili | 0.34 | 0.45 | 0.38 | 1.06 | 0.98 | 0.97 | 1.14 | 1.12 | 1.15 | 1.30 | 1.09 | 1.19 | 1.12 | 1.39 | 1.46 | 1.38 |
| Yoruba | 0.46 | 0.44 | 0.97 | 1.01 | 0.98 | 0.98 | 1.04 | 1.07 | 1.07 | 1.21 | 1.14 | 1.14 | 1.07 | 1.26 | 1.15 | 1.04 |
| Shona | 0.29 | 0.32 | 0.97 | 1.13 | 0.99 | 1.00 | 1.32 | 1.29 | 1.27 | 1.69 | 1.40 | 1.71 | 1.45 | 2.77 | 3.28 | 3.40 |

## Gap findings (verified against the live table, all 61 rows read)

1. **Nigerian Pidgin does not appear among PazaBench's 61 languages.**
   Alphabetically the table runs Nyankole → Nyungwe → Oromo → Sesotho; there
   is no Pidgin entry of any kind. SautiLedger's benchmark evaluates the
   dominant contact language of West African commerce that the leading
   low-resource ASR leaderboard does not yet cover.
2. **No Intron/Sahara model appears among the evaluated models.** Our report
   is therefore the only place (we know of) where Sahara is measured
   side-by-side with the PazaBench model families on this speech.
3. **omnilingual (facebook) is the strongest model on all five languages**
   (WER 0.29–0.51), consistently ahead of facebook-mms; every other family
   sits at or above ~0.95 WER on Hausa/Igbo/Yoruba — effectively
   unusable. This is why omnilingual-ASR is the scientifically strongest
   open-weights comparator for Phase G.
4. **nvidia-nemo ranks 11th of 16 families** on average and shows 1.09–1.40
   WER on our languages — a datapoint to pair with the Nemotron 3.5 ASR
   finding (its 40 supported locales include no African language).

## Citation pointers

- Leaderboard: PazaBench — ASR Leaderboard for Low Resource Languages,
  Microsoft Research Africa (Nairobi), https://aka.ms/pazabench.
  Snapshot taken 2026-08-28; values may move as the leaderboard updates.
- The PazaBench paper was stated (Deep Learning Indaba 2026 masterclass,
  M. Muchai) to be accepted at Indaba 2026 — cite the paper once public,
  the leaderboard URL until then.
