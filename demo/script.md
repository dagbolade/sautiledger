# SautiLedger — the 90-second demo

Start: `python -m sautiledger.demo` (= `make demo`), open http://127.0.0.1:8090.
Ledger is empty, egress meter reads **0.00 KB** in green.

## (a) Pidgin sale with a Yoruba number — ~20s
Say (or type): **"I don sell three derica of rice five thousand five"**
- Agent replies and reads back: *"Logged: 3 derica of rice, five thousand
  five hundred naira. Correct?"*
- Point at the ledger panel: entry + running total appeared.
Then: **"sell garri egberun meta"** — "egberun meta" is Yoruba for 3,000.
Same ledger, no language switch, no settings.

## (b) Native grammar + the safety clarify — ~25s
Say: **"customer take two paint rubber of garri two two fifty"**
- Logs in ONE turn: 250 each, 500 total. Reduplicated money is the
  distributive in Pidgin — a rule an outsider hears as ambiguous. The
  line for the judges: *the corpus itself needed native-speaker
  correction; that correction became a grammar rule in the language pack.*
Then: **"I don sell garri finish"** — a sale with no amount spoken.
- The agent does NOT log. It asks, market-natural: *"How much you sell
  the garri?"* Answer: **"five thousand"** → entry logs at 5,000.
- *A confident wrong entry in someone's money records is the worst
  possible failure — so the agent never guesses an amount.*

## (c) The sovereignty moment — ~20s
Kill the wifi (or restart with `SAUTI_MODE=offline`).
Say: **"sell pure water two bag one two"** — still works. Everything on
screen — parsing, agent, ledger — is running on this device.
Point at the meter: **0.00 KB, green.**

## (d) Ask the ledger — ~10s
Say: **"abeg how much I don make today"** → spoken total, from local SQLite.

## (e) Prove it — ~20s
Tap the egress meter. The transmission ledger opens: every clip that went
to Sahara — timestamp, purpose, bytes, disposition — and nothing else.
*The ledger, the transcripts, the questions: none of it ever left the phone.
With Sahara's offline deployment, even this list goes to zero.*
