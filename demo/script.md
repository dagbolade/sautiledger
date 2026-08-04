# SautiLedger — the 90-second demo

Start: `python -m sautiledger.demo` (= `make demo`), open http://127.0.0.1:8090.
Ledger is empty, egress meter reads **0.00 KB** in green.

## (a) Pidgin sale with a Yoruba number — ~20s
Say (or type): **"I don sell three derica of rice five k five"**
- Agent replies and reads back: *"Logged: 3 derica of rice, five thousand
  five hundred naira. Correct?"*
- Point at the ledger panel: entry + running total appeared.
Then: **"sell garri egberun meta"** — "egberun meta" is Yoruba for 3,000.
Same ledger, no language switch, no settings.

## (b) The ambiguity trap — ~20s
Say: **"customer take two paint rubber of garri two two fifty"**
- The agent does NOT log. It asks: *250 each (500 total), or 2,250 total?*
- Answer: **"each"** → entry logs at 250 each, 500 total.
- The line for the judges: *a confident wrong entry in someone's money
  records is the worst possible failure — so the agent refuses to guess.*

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
