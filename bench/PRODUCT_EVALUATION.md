# Product evaluation

Run `python -m bench.explorer --serve --port 8094` and open http://127.0.0.1:8094/.
This generates `static/benchmark/data.json` and `bench/results/conversations.json`.
Use `--no-audio` to disable local corpus playback. The static export contains no
audio files; it can also be opened at `/static/benchmark/index.html` in the app.

The speech view reads the existing cached `bench/results/metrics.json`; it does
not rerun ASR or rewrite scores. It shows 70 unique clip keys, while the source
metadata declares 76. Historical and raw-ablation controls are labelled and
excluded from the default seven-system comparison. Broadcast speech has no
transaction ground truth, so transaction metrics are unavailable for that tier.

`python -m bench.conversations` replays the current transcript
scenarios in `conversation_scenarios.json` (37 scenarios: 19 completion tasks and 18 controls; see the generated summary for results) through the real agent and an isolated SQLite ledger, with the app's
English reply renderer. It reports exact final ledger completion, turns to a
correct entry, turns to confirmation, local processing time, and wrong amounts
committed at any turn: even if corrected later. A safe unanswered clarification
does not count as a completed transaction. Every turn includes before/after
ledger evidence. Source and implementation hashes make results traceable.

These are scripted development checks, not held-out results or a human study.
Timing excludes ASR, TTS, network and human response time. The five deliberately seeded error
scenarios demonstrate repair paths; they do not measure how often people notice
errors. That requires consenting participants, randomised error trials and actual
task-time/error-detection observations. Do not present these results as human
completion or detection rates. Existing benchmark scores remain separate.

The app's structured readback comes from actual pending/recorded agent state.
It preserves the full reply, persistent confirmation controls and editable input.
Amount corrections now re-enter confirmation, allowing rejection to void them.

Speech/reply choices are English/Pidgin/Yoruba with English or Pidgin replies,
and Shona/English with English replies. English is the interface language. The Nigerian pack defaults to Pidgin replies; English is selectable. Native Shona replies still require validation; they are not claimed.
Choice is saved per device and routes the speech-pack hint as well as reply
rendering. Switching is blocked during a pending question. Currency switches
require an empty book. English and Pidgin use their matching Intron voice languages in cloud mode;
English accents and voice gender are selectable. Browser speech is offline-only. Retention consent is independent and defaults off.

Public artifacts redact AfriSwitch reference and hypothesis text (including the
tracked metrics and static explorer export) while preserving all numeric scores.
`bench.publication.public_row` protects the benchmark writer; the explorer also
redacts an older unredacted source. The local raw cache remains ignored. Existing
Git history and any already deployed artifacts are not rewritten by this change.

## Hosted-demo privacy

On the hosted demo, SAUTI_AGENT=hosted is enabled: utterance text the grammar cannot parse may be sent to the Hugging Face inference router (router.huggingface.co). Each call is listed as "agent fallback (hosted model)" in the in-app transmission list. Self-hosted setups can disable remote fallback with SAUTI_AGENT=none or use auto for local Ollama only. Audio is sent to Sahara for transcription; reply text is sent for online TTS. These texts and audio can contain transaction details. The ledger database itself is not uploaded to these services.

Yoruba/English replies are available as a beta for the Nigerian pack, with Intron language `yo` and accent `yoruba`. Core sale/expense confirmations and common questions use Yoruba; monetary phrases, item names and unmatched messages retain English/original text. Native-speaker listening validation is still required. The welcome guide advances every 12 seconds, pauses on interaction or reduced-motion preference, and never advances past the privacy/consent slide automatically.
