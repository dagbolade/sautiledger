# Ethics, Privacy & Inclusion Note

**SautiLedger · Sahara CodeSwitch Africa Challenge (Phase 2)**

Our users are market traders handing their money records to software. The
commitments below are implemented and testable, not aspirational.

## 1. Privacy: where the money records actually live

Sales, expenses, credit and customer notes are never transmitted to any
third party — not to a model, not to a vendor. The only data that ever
leaves the application is **audio**, sent for transcription, and **reply
text**, sent to generate the spoken confirmation.

**Where the ledger is stored depends on how the app is deployed, and we
state both rather than claiming the stronger one:**

- **Self-hosted** (`make phone` — the intended production shape): the
  SQLite ledger is on the trader's own device. Nothing but audio and reply
  text crosses the network.
- **Hosted demo** (the Railway instance our field testers used): the
  SQLite ledger is on a server volume that we operate, and the utterance
  reaches our backend on its way to Sahara. Per-device cookies give each
  trader a separate ledger from every other trader; **they do not make the
  storage phone-local.** A trader using the hosted instance is trusting us
  as an operator.

We ran the hosted instance because it was the only way to get real traders
using the app from their own phones, without installing anything, inside
the challenge window. That was a deliberate trade of storage locality for
testability, and the honest description of it belongs here rather than in
a footnote. For a real deployment the self-hosted mode is the one we would
ship, and the code path is identical.

The following are enforced structurally, in both modes:

- Exactly one module (`egress.py`) may open a network connection. A test
  in the suite parses every other module's AST and fails the build if any
  of them imports an HTTP or socket library. The one sanctioned exception
  (the WebSocket library, for streaming) is allowlisted to that file alone.
- Every transmission — each clip, each TTS request, each streamed chunk
  with its byte total — is written to a transmission ledger and displayed
  to the user in plain language, in their own register: *"your voice clip,
  sent for transcription."* The counter is visible on the main screen at
  all times, not buried in settings.

## 2. Consent: opt-in, revocable, and narrow

Voice-clip retention is **off by default**. It is enabled only by an
explicit toggle, worded in Pidgin, that appears both in the privacy sheet
and in the first-run welcome guide:

> *"Keep my voice clips make dem help test the speech model. Na only if
> you gree — you fit off am anytime. Clips stay for this app, nowhere
> else."*

That last sentence constrains us, and we treat it as binding. It permits
retention for model testing; it does **not** permit redistributing a
trader's voice into a public benchmark corpus. Our own bundling tool
(`tools/curate_audio_bundle.py`) therefore **refuses to produce a
shareable bundle** unless each contributing session is explicitly listed
as having given fresh, separate permission, with the date and wording
recorded in the bundle's `CONSENT.md`. Running it without that returns:

> `REFUSED: the in-app consent says clips 'stay for this app, nowhere
> else' — it does not cover sharing in a benchmark bundle.`

We would rather submit fewer audio samples than samples our users did not
knowingly agree to share.

## 3. De-identification

Where clips are shared with consent, the bundle carries **no transcripts
and no names** — only a four-character session reference, duration,
language, domain and device type. Transcripts are withheld by default
precisely because market speech contains customers' names ("Mr Olaolu…").
The bank statement export follows the same rule: it prints
`Statement ref 671E`, never a raw session identifier.

## 4. Safety: a wrong number is the harm

For a bookkeeping agent, the safety failure is not offensive output — it
is a wrong amount silently entering someone's financial record.

- **Never fabricate an amount.** Any figure the grammar cannot justify
  becomes a question, never a value. The LLM fallback's output is
  discarded if it contains a number not present in the utterance.
- **Ask rather than assume.** Genuinely ambiguous pricing produces a
  clarifying question. Our benchmark reports "amount safe" (correct *or*
  asked) as a first-class outcome for this reason.
- **Refuse incoherence.** A readback that would echo garbled text is
  refused outright rather than offered for a tired "yes".
- **Corrections void, never overwrite.** A rejected entry is marked
  voided and stays visible — the book records that a mistake was made and
  removed, which is what an auditor and a lender both need.

This was tested by reality. On 27 August a live user's spoken "5700" was
merged by ASR into "570007" and entered her ledger. She caught and voided
it; we root-caused the exact unguarded path from the usage log, closed it
everywhere, and replay-tested it against her real transcripts. The
incident is documented in the repository rather than hidden.

## 5. Bias awareness and inclusion

- **No language ships without a native speaker.** Every pack's test corpus
  was drafted, then *corrected* by a native speaker before recording. Our
  own AI-drafted Pidgin was wrong in ways only a native ear caught
  (reduplicated money is a distributive, not an ambiguity); the same
  process for Shona taught us `hwani`, concord prefixes on code-switched
  numerals, and that traders quote in US dollars. Packs without that
  validation (`sw-KE`, `ha-NG`) are labelled unvalidated rather than
  presented as finished.
- **We report disparity, not just averages.** Following ASR-FairBench
  (Rai et al., Interspeech 2025), which the organisers recommended, our
  benchmark reports per-group word error rates and a worst-to-best
  disparity ratio, because an aggregate score hides exactly the users this
  product exists for.
- **We predicted our own weak spot in public, in advance.** Shona is a
  supported Sahara language but not one of its documented code-switch
  pairs, so we registered the prediction that our Shona tier would perform
  worse — in a committed file, before any Shona audio existed — and then
  reported the result either way.

## 6. Responsible data use

- **AfriSwitch** (CC BY-NC-SA 4.0) is used for **evaluation only**, fetched
  at run time, never redistributed, and never used to train or tune
  anything.
- **No training on user data.** Retained clips are used to reproduce and
  fix failures, not to fit a model.
- **Nothing sensitive is committed.** Audio, ledgers, recordings and API
  keys are gitignored; the repository was audited and its history rewritten
  before publication to guarantee it.
- **Vendor data-retention settings** are configurable in the Intron console
  and are part of the deployment checklist, not an afterthought.

## 7. Dignity

The app speaks the user's language, including her errors' language. It
does not correct her grammar, transliterate her speech into standard
English, or ask her to talk differently so the machine can cope. When it
does not understand, it says so plainly and asks again — because the
alternative, quietly guessing at someone's money, is the one thing a
ledger must never do.
