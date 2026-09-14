# Submission checklist: Sahara CodeSwitch Africa Challenge (Phase 2)

**Deadline: 15 September 2026, 11:59pm WAT. Target: submit on the 14th.**
**One submission per access token, there is no second attempt.** Log in
with the registered email and the access token from Intron's confirmation
email (never stored in this repo).

**Category:** the form has no category field; SOLUTION.md names Fintech, Telco & Call Center.

---

## The submission form, field by field

| Form field | Status | Where |
|---|---|---|
| Website, title, questions 1-8 | ready to paste | [`submission/FORM-ANSWERS.md`](FORM-ANSWERS.md) |
| Demo video URL (unlisted YouTube, max 5 min) | **needs filming** | script: [`demo/script-phase2.md`](../demo/script-phase2.md) |
| Benchmark report link (PDF, max 3 pages) | PDF ready; **needs the Hugging Face link, then upload to Google Drive** | [`submission/SautiLedger-Benchmark-Report.pdf`](SautiLedger-Benchmark-Report.pdf) |
| Benchmark audios link (optional) | folder built (45 clips, 3 consenting speakers); **needs uploading to Hugging Face** | `Downloads/sautiledger-market-speech` |

## Links to paste into the form

- **Repository:** https://github.com/dagbolade/sautiledger
- **Live app:** https://sautiledger-production.up.railway.app
- **Benchmark report:** Google Drive link to the PDF (the full report is at https://github.com/dagbolade/sautiledger/blob/main/bench/results/REPORT.md)
- **Demo video:** _(paste the unlisted YouTube link once filmed)_

## What the benchmark satisfies

The rule is Sahara plus **two or more** other speech models. We compare
**seven ASR systems**: `sahara-v2.5`, Microsoft `mai-transcribe-2`,
OpenAI `gpt-4o-transcribe`, NVIDIA `parakeet-tdt`, Google `chirp-3`,
`whisper-large-v3` and Meta's `omnilingual-ctc-300m`, plus a frozen
5 August Sahara snapshot used as a drift control (not counted as a
system), and **two TTS configurations** benchmarked by round trip, because
Intron confirmed on 9 September that teams using TTS should benchmark it
too.

`whisper-small` was retired: it had been a placeholder for a frontier
model we had no key for, and was replaced by MAI-Transcribe-2 rather than
left in as filler. `whisper-large-v3` stays as the open-model baseline.
The report states this so the swap cannot read as dropping an
inconvenient result.

---

## Before you submit: the human items

1. **Field data (highest value).** Get your sister and Idowu using the
   current build for a few days. It improves three things at once: the
   first-try-logged rate in the dashboard, the bank statement's
   "sales on N of 7 days" line, and the consented audio bundle.
   Ask them to turn the **voice-clips toggle on** in Privacy.
2. **Fresh consent for the audio bundle.** The in-app consent says clips
   "stay for this app, nowhere else": that does **not** cover sharing
   with Intron. Ask each tester explicitly, record the date and wording,
   then run:
   ```
   python tools/curate_audio_bundle.py stage --clips <session>-clips.zip \
       --usage <session>-usage.csv --session <session-id>
   # read bundle-staging/REVIEW.md, delete any clip naming a person
   python tools/curate_audio_bundle.py finalize \
       --consent-confirmed <session-id> --consent-note "how and when they agreed"
   ```
   The tool refuses to build a bundle without this. If consent doesn't
   come through, **submit without the audio**: the bonus is not worth
   sharing someone's voice they didn't agree to share.
3. **Shona wild tier (optional).** Ask the validator to type what she said
   in clips *Ruwa 17-35*; those 19 unscripted market phrases become a
   second Shona tier.
4. **Void the two stale rows** in your sister's ledger (the ₦50 "per" row
   and the ₦4,000 "choco ball pack is" row), or fix them in-app with
   "no, na …". Both predate the field-round-two fixes.
5. **Per-tester statements.** Once they have real days logged:
   `/admin/statement?session=<id>&period=week`, worth eyeballing before
   the judges do.

## Final pre-flight

- [ ] `python -m pytest` green (272 tests on 14 September; rerun after any further code change)
- [ ] `python -m bench.run --score-only` regenerates the report cleanly
- [ ] Live app answers on a phone, mic works, readback audible
- [ ] Demo video uploaded **unlisted** and the link opens in a private window
- [ ] No secrets in the repo (`git log -p | grep -i "api_key"` returns nothing meaningful)
- [ ] Read `REPORT.md` top to bottom once more: it is 30% of the score

## Final link verification

Demo video URL: **awaiting David**. Native-audio Hugging Face dataset URL: **awaiting David**. Verify both in a private browser before submitting; do not treat publication as verified until those links work.

Production keeps `SAUTI_AGENT=hosted`. Unparsed utterance text may go to `router.huggingface.co`, labelled `agent fallback (hosted model)` in the transmission list. Audio and reply text go to Sahara. Self-hosted `none` or `auto` disables remote fallback. No Railway configuration change is needed.
