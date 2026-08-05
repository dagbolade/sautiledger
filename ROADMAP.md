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
