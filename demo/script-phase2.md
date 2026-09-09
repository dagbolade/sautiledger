# SautiLedger — Phase 2 demo video script (~2:40)

Shoot on a **phone**, using the live deployment
`https://sautiledger-production.up.railway.app` (installed to the home
screen so there is no browser chrome). Real product, real network, no
localhost. Speak the lines yourself; the sound of a real voice in a real
room is the point.

**Before you start:** open the app, clear the day if needed, and check the
egress strip reads a low number in green. Have the volume up — the
readback voice is part of the demo.

---

## 0:00–0:15 · The problem

*On camera or voiceover, over a shot of a market stall or your sister's
stock:*

> "My sister sells eggs. She sells forty times a morning with her hands
> full. Her books live in her head — so when a bank asks what her business
> earns, there's nothing to show. Not because the business is small.
> Because nobody built a book she could keep while trading."

---

## 0:15–0:50 · The core loop, in her actual language

Hold the mic button and say, naturally:

> **"I don sell three derica of rice five thousand five"**

Show: the transcript appears, the entry lands in the ledger, the total
counts up — **and let the readback play out loud**: *"Logged: 3 derica of
rice, five thousand five hundred naira. Correct?"*

*Voiceover, while that happens:*

> "One sentence, three languages — Pidgin, English, a Yoruba measure. And
> it answers in a Nigerian voice, because it has to be checkable by ear.
> This isn't transcription. The voice did something: it wrote a row."

Then, without touching a setting:

> **"customer take two paint rubber of garri two two fifty"**

> "'Two two fifty' is not ambiguous to a trader — reduplicated money is
> the per-unit price. We only know that because a native speaker corrected
> us. That correction is now a rule in the language pack."

---

## 0:50–1:20 · It's an agent, not a dictaphone

> **"wetin remain?"**

Show the spoken answer with real arithmetic over the real rows.

> **"I buy fuel ten thousand naira"** → then **"no, na five thousand"**

Show the correction: the wrong row is **voided, not deleted** — it stays
visible.

> "Corrections void rather than overwrite. The book records that a mistake
> was made and removed — which is exactly what a lender needs to trust it."

---

## 1:20–1:50 · The part that matters: it refuses to guess

> **"I don sell garri finish"** — a sale with no price spoken.

Show that **nothing is written**, and it asks: *"How much you sell the
garri?"* Answer **"five thousand"** and let it log.

*Voiceover — this is the emotional centre of the video:*

> "On the 27th of August a real user said 'five thousand seven hundred'.
> The speech model heard five hundred and seventy thousand and seven. The
> entry that reached her ledger was wrong by a hundred times. She caught
> it, and it's still in her book — voided, on the record. We traced the
> exact code path that let it through and closed it everywhere. Now a
> number with a strange shape gets read back before anything is written.
> A ledger that guesses is worse than no ledger."

---

## 1:50–2:10 · Privacy you can watch

Open the privacy sheet. Point at the transmission list and the counter.

> "Her money records never leave the phone. The only thing that goes out
> is the audio, and every single byte is listed here in her own language.
> Keeping voice clips is off by default — she turns it on, or it doesn't
> happen."

---

## 2:10–2:35 · The reason a bank cares

Tap **Export my statement**.

> "Totals, net position, average daily revenue, and how many of the last
> seven days actually have sales in them — the consistency a lender
> actually asks about. It says plainly that it's transaction history, not
> a credit score. For a trader with no formal books, this is the first
> document she's ever been able to hand anyone."

---

## 2:35–2:40 · Close

> "Five languages. Built with Sahara, benchmarked against four other
> speech systems, and tested by traders who don't care what any of it is
> called — only whether the number is right."

---

## Optional insert · Shona (shoot separately if you want it)

The deployed instance runs the Nigerian pack; the Shona pack ships in the
repo with its own native-recorded test tier. To show it, run locally:

```
SAUTI_PACK=sh-ZW .venv/Scripts/python -m sautiledger.phone
```

and say **"Ndatengesa matomatisi ethree dollars"**. Worth 10 seconds if
you want the multilingual claim on screen rather than only in the report —
otherwise leave it to the report, which has the full Shona benchmark.

---

## Practical notes

- **Landscape**, phone braced or propped; don't narrate over the readback
  — let the app's voice be heard at least once, clean.
- If a take mishears you, **keep it in**. A clarify question on camera is
  a feature: it shows the agent asking instead of inventing.
- Upload **unlisted** to YouTube; paste the link in the submission form.
- Keep it under three minutes. Judges are watching many of these.
