# Submission checklist — Sahara CodeSwitch Africa Challenge (Phase 2)

**Deadline: 15 September 2026, 11:59pm WAT. Target: submit on the 14th.**
**One submission per access token — there is no second attempt.** Log in
with the registered email and the access token from Intron's confirmation
email (never stored in this repo).

**Category to select:** Fintech, Telco & Customer Experience.

---

## The six required items

| # | Item | Status | Where |
|---|---|---|---|
| 1 | Solution description | ready | [`submission/SOLUTION.md`](SOLUTION.md) |
| 2 | Demo video (unlisted YouTube) | **needs filming** | script: [`demo/script-phase2.md`](../demo/script-phase2.md) |
| 3 | Code / technical documentation | ready | repo root [`README.md`](../README.md) + [`CONSTRAINTS.md`](../CONSTRAINTS.md) |
| 4 | Benchmark report (3+ models incl. Sahara) | ready | [`bench/results/REPORT.md`](../bench/results/REPORT.md) |
| 5 | Ethics / inclusion note | ready | [`submission/ETHICS.md`](ETHICS.md) |
| 6 | Benchmark audios (optional, bonus points) | **blocked on consent** | see below |

## Links to paste into the form

- **Repository:** https://github.com/dagbolade/sautiledger
- **Live app:** https://sautiledger-production.up.railway.app
- **Benchmark report:** https://github.com/dagbolade/sautiledger/blob/main/bench/results/REPORT.md
- **Demo video:** _(paste the unlisted YouTube link once filmed)_

## What the benchmark satisfies

The rule is Sahara plus **two or more** other speech models. We compare
**four ASR systems** — `sahara-v2.5`, `whisper-large-v3`, `whisper-small`,
and Meta's `omnilingual-ctc-300m` — plus a frozen 5 August Sahara snapshot
used as a drift control (not counted as a system), and **two TTS
configurations** benchmarked by round trip, because Intron confirmed on
9 September that teams using TTS should benchmark it too.

---

## Before you submit — the human items

1. **Field data (highest value).** Get your sister and Idowu using the
   current build for a few days. It improves three things at once: the
   first-try-logged rate in the dashboard, the bank statement's
   "sales on N of 7 days" line, and the consented audio bundle.
   Ask them to turn the **voice-clips toggle on** in Privacy.
2. **Fresh consent for the audio bundle.** The in-app consent says clips
   "stay for this app, nowhere else" — that does **not** cover sharing
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
   come through, **submit without the audio** — the bonus is not worth
   sharing someone's voice they didn't agree to share.
3. **Shona wild tier (optional).** Ask the validator to type what she said
   in clips *Ruwa 17–35*; those 19 unscripted market phrases become a
   second Shona tier.
4. **Void the two stale rows** in your sister's ledger (the ₦50 "per" row
   and the ₦4,000 "choco ball pack is" row), or fix them in-app with
   "no, na …". Both predate the field-round-two fixes.
5. **Per-tester statements.** Once they have real days logged:
   `/admin/statement?session=<id>&period=week` — worth eyeballing before
   the judges do.

## Final pre-flight

- [ ] `python -m pytest` green (183 unit tests at last run)
- [ ] `python -m bench.run --score-only` regenerates the report cleanly
- [ ] Live app answers on a phone, mic works, readback audible
- [ ] Demo video uploaded **unlisted** and the link opens in a private window
- [ ] No secrets in the repo (`git log -p | grep -i "api_key"` returns nothing meaningful)
- [ ] Read `REPORT.md` top to bottom once more — it is 30% of the score
