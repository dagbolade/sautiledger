# SautiLedger — Phase 2 demo video script (~3:00)

**Form rules:** max 5 minutes · public or **unlisted** YouTube · must show
code-switching. This script runs about 3 minutes.

**Every spoken line below was rehearsed on 13 September through the same
code that is deployed**, and the app's reply is written under it. If
the app says something different on camera, the speech recogniser heard
you differently. Keep the take: an honest clarifying question is part of
the story.

Shoot on a **phone** against the live app
`https://sautiledger-production.up.railway.app` (added to the home screen,
so no browser bar). Volume up: the spoken read-back is part of the demo.

**Before you start**
- Language menu (top of the book): **English / Pidgin / Yoruba → Pidgin**.
- Start from an empty day, so the totals on screen match what you say.
- Landscape, phone propped. Quiet room.

---

## 0:00–0:15 · The problem

*On camera or voiceover, over a shot of a stall or stock:*

> "A market trader sells forty times a morning with her hands full. Her
> books live in her head, so when a bank asks what the business earns,
> there's nothing to show. Not because the business is small, but because
> nobody built a book she could keep while trading."

---

## 0:15–0:50 · The core loop, in her language

Hold the mic and say:

> **"I don sell three derica of rice five thousand five"**

App (spoken aloud): *"Logged sale: 3 derica of rice, five thousand five
hundred naira. Correct?"* → say **"yes"** → *"Noted. Ledger correct."*

*Voiceover while it plays:*

> "One sentence, three languages: Pidgin, English, and derica, a Nigerian
> market measure. The voice didn't just become text. It wrote a row, and
> it read the row back so she can check it by ear."

> **"customer take two paint rubber of garri two two fifty"**

App: *"Logged sale: 2 paint rubber of garri, two hundred fifty naira each,
five hundred naira total. Correct?"* → **"yes"**

> "'Two two fifty' means two hundred and fifty each. Every trader knows
> that. We only know it because a native speaker corrected us, and that
> correction is now a rule in the language pack."

---

## 0:50–1:20 · It's an agent, not a dictaphone

> **"wetin remain"**

App: *"You sell six thousand naira, you spend zero naira — wetin remain na
six thousand naira."*

> **"I buy fuel ten thousand naira"** → App: *"Logged expense: fuel, ten
> thousand naira. Correct?"*

> **"no, I buy fuel five thousand naira"** → App: *"Logged expense: fuel,
> five thousand naira. Correct?"* → **"yes"**

Point at the entries: the ₦10,000 row is **voided and still visible**, and
the ₦5,000 row replaces it.

> "A correction doesn't erase anything. The book shows that a mistake was
> made and fixed, which is exactly what a lender needs in order to trust it."

⚠ Say the correction exactly like that, the full sentence. Two shorter
forms currently misbehave (see *Known issues* below).

---

## 1:20–1:50 · It refuses to guess

> **"I don sell garri finish"**, a sale with no price.

App: *"How much you sell the garri?"* Nothing is written.
Say **"five thousand"** → *"Logged sale: garri, five thousand naira.
Correct?"* → **"yes"**

*Voiceover, the heart of the video:*

> "On the 27th of August a real user said 'five thousand seven hundred'.
> The speech model heard five hundred and seventy thousand and seven, and
> the entry reached her ledger wrong by a factor of a hundred. It's still
> in her book, voided, on the record. We closed that path everywhere: an
> amount with a strange shape is now read back before anything is written.
> A ledger that guesses is worse than no ledger."

---

## 1:50–2:15 · Shona, same app

Switch the language menu to **Shona / English → English · USD**.

> **"Ndatengesa matomatisi ethree dollars"**

App: *"Logged sale: matomatisi, three dollars. Correct?"* → **"yes"**

> **"Ndatengesa three cups dze rice nefive dollars fifty"**

App: *"Logged sale: 3 cup of rice, five dollars fifty cents. Correct?"* →
**"yes"**

> "Shona and English, in US dollars and cents, because that's how
> Zimbabwean traders price. A native Shona speaker wrote and recorded
> these phrases for our benchmark. Adding a language meant adding data,
> not rewriting the app."

*(If your Shona pronunciation gets misheard, that is fine to show: the app
asks instead of guessing. Or play one of her recorded clips from a second
device into the mic.)*

---

## 2:15–2:35 · Privacy you can see

Tap the **Privacy ↗** strip above the book and point at the transmission list.

> "The only thing that leaves for the speech service is the audio, and
> every transmission is listed here in plain language. Keeping voice clips
> is off unless she turns it on. On this hosted demo her book is stored on
> our server; run it yourself and it stays on her own phone."

---

## 2:35–2:50 · Why a bank cares

Tap **Trading statement**.

> "Totals, net position, average daily takings, and how many days actually
> had sales: the consistency a lender asks about. It says plainly that it's
> a transaction history, not a credit score."

---

## 2:50–3:00 · Close

> "Pidgin, Yoruba, English and Shona. Built on Sahara, benchmarked against
> six other speech systems on whether the money survives, not just the
> words, and tested on real phones."

---

## Known issues (found in rehearsal, 13 September; do not film these)

- **"no, na five thousand"** (amount only) voids the entry and then asks
  *"Wetin she buy?"* instead of replacing it.
- **"no, na fuel five thousand"** after an *expense* re-logs it as a
  **sale**, flipping the money direction.
- **"no no na five thousand"** corrects the amount in place. It works,
  but no voided row is left on screen, so it doesn't show the audit trail.

## Practical notes

- If a take mishears you, keep it. A clarifying question on camera shows
  the agent asking instead of inventing.
- Don't talk over the read-back. Let the app's voice be heard clearly at
  least once.
- Upload **unlisted**; paste the link into the form.
