# Product evaluation

Run `python -m bench.explorer --serve --port 8094` and open http://127.0.0.1:8094/.
This generates `static/benchmark/data.json` and `bench/results/conversations.json`.
Use `--no-audio` to disable local corpus playback. The static export contains no
audio files; it can also be opened at `/static/benchmark/index.html` in the app.

The speech view reads the existing cached `bench/results/metrics.json`; it does
not rerun ASR or rewrite scores. It shows 70 unique clip keys, while the source
metadata declares 76. Historical and raw-ablation controls are labelled and
excluded from the default eight-system comparison. Broadcast speech has no
transaction ground truth, so transaction metrics are unavailable for that tier.

`python -m bench.conversations` replays eight developer-authored transcript
scenarios through the real agent and an isolated SQLite ledger, with the app's
English reply renderer. It reports exact final ledger completion, turns to a
correct entry, turns to confirmation, local processing time, and wrong amounts
committed at any turn—even if corrected later. A safe unanswered clarification
does not count as a completed transaction. Every turn includes before/after
ledger evidence. Source and implementation hashes make results traceable.

These are scripted development checks, not held-out results or a human study.
Timing excludes ASR, TTS, network and human response time. The two injected error
scenarios demonstrate repair paths; they do not measure how often people notice
errors. That requires consenting participants, randomised error trials and actual
task-time/error-detection observations. Do not present these results as human
completion or detection rates. Existing benchmark scores remain separate.

The app's structured readback comes from actual pending/recorded agent state.
It preserves the full reply, persistent confirmation controls and editable input.
Amount corrections now re-enter confirmation, allowing rejection to void them.

Speech/reply choices are English/Pidgin/Yoruba with English or Pidgin replies,
and Shona/English with English replies. English is the interface and reply
default. Native Shona replies still require validation; they are not claimed.
Choice is saved per device and routes the speech-pack hint as well as reply
rendering. Switching is blocked during a pending question. Currency switches
require an empty book. English and Pidgin use their matching Intron voice languages in cloud mode;
English accents and voice gender are selectable. Browser speech is offline-only. Retention consent is independent and defaults off.

Public artifacts redact AfriSwitch reference and hypothesis text (including the
tracked metrics and static explorer export) while preserving all numeric scores.
`bench.publication.public_row` protects the benchmark writer; the explorer also
redacts an older unredacted source. The local raw cache remains ignored. Existing
Git history and any already deployed artifacts are not rewritten by this change.
