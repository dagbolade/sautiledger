# SautiLedger: Phase 2 demo video script (~2:50)

**Form rules:** max 5 minutes · public or **unlisted** YouTube · must show
code-switching.

**This is a new demo, not the workshop one.** None of the workshop lines are
reused (no derica of rice, no "two two fifty" garri, no "garri finish", no
"how much I don make", no pure water). The story is an egg trader's day and
what Phase 2 added: credit, corrections that keep the audit trail, asking
for a missing price, profit and best-seller questions, English replies, the
lender statement, and the seven-system benchmark.

**Every line below was tested on 14 September**: spoken by both of Sahara's
Pidgin voices, transcribed by Sahara, and run on the live app. The reply
under each line is what the live app returned. If a take mishears you, keep
it; the app asking instead of guessing is part of the story.

Shoot on a **phone** against the live app
`https://sautiledger-production.up.railway.app` (added to the home screen).
Volume up: the spoken read-back is part of the demo.

**Before you start**
- Language menu (top of the book): **English / Pidgin / Yoruba → Pidgin**.
- Use a fresh, empty book (private browser window), so the totals match.
- Landscape, phone propped, quiet room.

**How to say amounts (tested):** say single thousands the way traders do,
"four thousand", "eight thousand", "six thousand naira". Sahara drops the
"thousand" in bigger compound amounts such as "ten thousand" (heard as
1000) or "five thousand five hundred" (heard as 500), so this script avoids
them.

---

## 0:00-0:15 · The problem

*On camera, or voiceover over eggs or a stall:*

> "My sister sells eggs. Some customers pay later, prices change by the
> crate, and all of it lives in her head. When a lender asks what the
> business earns, there's nothing to show."

---

## 0:15-0:40 · A sale on credit, in her language

Hold the mic and say:

> **"I don sell two crate of egg four thousand each"**

App (spoken aloud): *"Logged sale: 2 crate of egg, four thousand naira each,
eight thousand naira total. Correct?"*

Then, straight away:

> **"that one na credit, she go pay on Friday"**

App: *"Noted: last entry na credit, she go pay friday. I dey watch am."*

*Voiceover:*

> "Pidgin, English numbers, a market unit, and the app works out the total.
> Credit is recorded with the day it's due, because that's how traders
> actually sell."

---

## 0:40-1:05 · A mistake, fixed on the record

> **"I buy fuel for eight thousand naira"**

App: *"Logged expense: fuel, eight thousand naira. Correct?"*

> **"no, I buy fuel five thousand naira"**

App: *"Logged expense: fuel, five thousand naira. Correct?"* → **"yes"**

Point at the entries: the ₦8,000 row shows **Voided** and stays visible; the
₦5,000 row replaces it.

> "Nothing is erased. The book shows the mistake and the fix, which is what
> a lender needs to trust it."

---

## 1:05-1:30 · It won't guess your money

> **"I sell one bag of beans"**, no price.

App: *"How much you sell the beans?"* Nothing is written yet.

> **"six thousand naira"**

App: *"Logged sale: 1 bag of beans, six thousand naira. Correct?"* →
**"yes"**

*Voiceover:*

> "In August a real user said five thousand seven hundred, and the speech
> model heard five hundred and seventy thousand. We closed that path: an
> amount the app isn't sure of is asked for or read back, never guessed."

---

## 1:30-1:50 · Ask the book

> **"wetin be my profit today"**

App: *"You sell fourteen thousand naira, you spend five thousand naira,
wetin remain na nine thousand naira."*

> **"wetin I sell pass this week"**

App: *"Your best seller today na egg, eight thousand naira."*

---

## 1:50-2:05 · Same book, English replies

Open the language menu and choose **English / Pidgin / Yoruba → English**.

> **"what are my sales today"**

App: *"Sales today: fourteen thousand naira from 2 sales."*

While the menu is open, let the camera see the **Shona / English · USD**
option too (don't select it; a book with entries can't change currency).

> "Replies in Pidgin, English or Yoruba, and the same app runs Shona and
> English in US dollars. A native Shona speaker recorded our Shona test set."

---

## 2:05-2:20 · What a lender sees

Tap **Trading statement**.

> "Sales, spend, what's owed on credit and how many days had trading. It
> says plainly that it's a transaction history, not a credit score."

---

## 2:20-2:35 · What leaves the phone

Tap the **Privacy ↗** strip and point at the list.

> "Every transmission is listed. Audio and the read-back text go to Sahara;
> on this hosted demo, a sentence the grammar can't parse may go to a
> Hugging Face model, and it's listed too. Keeping voice clips is off unless
> she turns it on."

---

## 2:35-2:50 · Why Sahara, measured

Open `https://sautiledger-production.up.railway.app/static/benchmark/index.html`.

> "We tested seven speech systems on whether the money survives, not just
> the words, on Pidgin, Shona and Yoruba speech recorded for the benchmark. No
> system wins everywhere, so we built a ledger that stays safe whatever the
> speech model hears. Report and dataset are public."

---

## Practical notes

- Speak at normal market pace; say "four thousand", not "four k".
- Don't talk over the read-back. The first read-back can take up to about
  6 seconds; later repeated replies are instant.
- If a take mishears you, keep it. A clarifying question on camera shows the
  agent asking instead of inventing.
- Upload **unlisted**; paste the link into the form.
