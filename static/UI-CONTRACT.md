# UI handoff contract

**For a designer or agent rebuilding the front end.** The visual layer is
yours — layout, motion, type, colour, components, all of it. This file
records the parts that are *not* cosmetic, because they are either graded
in the competition submission or load-bearing for safety.

Only `static/index.html` and `static/app.js` should change. **Do not edit
anything under `src/sautiledger/`** — that is the parser, the safety
gates and the API, and it is covered by 183 tests that a UI change should
never need to touch.

---

## 1. Four things that must survive any redesign

These are judged. Losing them costs more than any visual gain.

### a. The egress meter must stay visible without interaction

The strip showing bytes sent (`#egress`, `#egress-total`) is the single
most distinctive claim the product makes: *every byte that leaves this
device is counted, in the open.* It must be visible on the main screen at
all times — not behind a tap, not in a settings page, not only in the
privacy sheet. Restyle it however you like; do not demote it.

### b. Voice-clip consent is OFF by default and explicitly opt-in

`#retain` (privacy sheet) and `#retain-ob` (welcome guide) are the same
setting. Rules:

- It must start **off**. Never pre-checked, never "on by default", never
  bundled into an "accept all" control.
- The wording must stay plain and honest. Current text: *"Keep my voice
  clips make dem help test the speech model. Na only if you gree — you fit
  off am anytime. Clips stay for this app, nowhere else."*
- The welcome guide must only ever POST an explicit **yes**. Skipping,
  dismissing or closing the guide must not enable retention.

### c. The readback and its "Correct?" turn

Every logged entry produces a confirmation ending in **"Correct?"**, and
the user's next utterance may reject it. This is the safety loop, not a
toast notification: the reply must be readable, and the input must stay
available so the user can answer. Do not auto-dismiss it, and do not
replace it with a non-blocking snackbar that scrolls away.

### d. Clarify questions are first-class replies

When the agent is unsure it asks a question instead of writing a row.
Those replies must render like any other agent message. If a redesign
hides or truncates them, the product's core behaviour becomes invisible.

---

## 2. API contract — do not change these shapes

All requests are same-origin. The `sauti_device` cookie carries session
identity; **always send credentials** (default `fetch` same-origin is
fine — do not switch to a cross-origin or no-cookie mode).

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/utterance` | POST | `FormData` with `text=…` **or** `audio=<blob>` | `{transcript, reply_text, parse, egress_delta, egress_total}` |
| `/state` | GET | – | `{mode, pack, entries[], total, retain_audio, tts, stream, egress{...}}` |
| `/consent` | POST | `FormData` `retain_audio=true|false` | `{retain_audio}` |
| `/tts` | POST | `FormData` `text=…` | `audio/wav` bytes, **or HTTP 204** |
| `/void/{id}` | POST | – | voids that row |
| `/statement` | GET | `?period=week` | printable HTML page |

Two behaviours are easy to break by accident:

- **`/tts` returning 204 is normal**, not an error. It means "use the
  browser voice" (offline mode, cap reached, or the cloud call failed).
  Keep the `speechSynthesis` fallback path; do not surface 204 as a
  failure to the user.
- **`egress_total` only ever grows.** Render it as a live counter; do not
  reset it on navigation.

## 3. Element ids currently wired in `app.js`

If you rename these, update `app.js` in the same change:

```
chat  close  consent  egress  egress-rows  egress-total  entries
guide  modal  mode  ob-consent  ob-next  onboard  retain
retain-ob  scroll  send  talk  talk-label  text  total
```

`#talk` is the push-to-talk control: **press and hold to record, release
to send**. It also needs a `.recording` state — the trader is in a market
and must be able to tell at a glance whether it is listening.

## 4. Things worth keeping (not graded, but hard-won)

- **PWA install**: `manifest.webmanifest` + `icon.png` + the apple meta
  tags. Testers install it to the home screen; losing that turns a product
  back into a web page.
- **Pidgin copy throughout**, including errors ("I no hear you well, abeg
  try again"). The app speaking the user's language is the point; do not
  standardise the strings into English.
- **`prefers-reduced-motion`** is respected. Keep it.
- **Sunlight legibility.** The warm-paper palette was chosen because the
  users are outdoors on market stalls. Any new palette needs real
  contrast in bright light — this is a functional constraint, not taste.
- **Streaming path** (`SAUTI_STREAM`): currently disabled server-side, but
  the client code paths exist. If they are in the way, leave them dormant
  rather than deleting them.

## 5. How to verify you have not broken anything

There are **no automated tests over the front end** — the 183 tests cover
the parser and API only. So a UI change is unguarded, and this checklist
is the safety net:

1. `python -m sautiledger.demo` → open `http://127.0.0.1:8090`
2. Type **"I don sell three derica of rice five thousand five"** → an
   entry appears, total updates, reply ends in **"Correct?"**
3. Type **"yes"** → *"Noted. Ledger correct."*
4. Type **"I don sell garri finish"** → **no row is written**, and it asks
   *"How much you sell the garri?"*
5. Answer **"five thousand"** → the row logs at 5,000
6. Open the privacy sheet → consent is **off**; the transmission list and
   byte total are present
7. Toggle consent on → it persists after a page reload (`/state` returns
   `retain_audio: true`)
8. Reload → the ledger and egress total are still there
9. On a phone (or narrow viewport): the mic control is reachable
   one-handed and readable in daylight
10. `python -m pytest -q` → still 183 passed (it should be untouched; if
    this fails, something outside `static/` was edited)

Finally, deploy to a preview and **check it on a real phone in daylight**
before it goes in front of judges. The last redesign passed on a desktop
monitor and failed the first time it was held up outdoors.
