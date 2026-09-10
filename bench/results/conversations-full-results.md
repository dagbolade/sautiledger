# Conversation benchmark — full results

Generated: 2026-09-10T20:22:21.167883+00:00
Commit: `97d30c6d84aca4a86bea9610a8e8376d4c674484`
Scenario SHA-256: `7acf0634bf56d127c71ff2686104e29c43d4bf0a571b42fab00d7cdc4af1568d`
Implementation SHA-256: `921fcd7f5b32169da706a58f9112ae252c34e8ef0728562fb1c3ae93ec9cdd32`

Local transcript replay through the real agent and isolated SQLite. English reply renderer; no ASR, TTS, network, LLM, or human timing. These are known development/field regressions, not held-out tests. The frozen speech benchmark was not rerun or overwritten.

## Summary

- Completion: 10/11 (90.91%).
- Controls: 1/1 remained incomplete.
- Median first-completion turn: 2.0
- Scenarios with an erroneous monetary entry at any turn: 3; with an erroneous final entry: 1.
- Total measured local processing: 7.330 ms.

The monetary-error metric matches type, currency and amount against expected rows; extra duplicates also count. Two scenarios deliberately inject a wrong initial amount. Queries are graded primarily by final ledger and pending state, not a dedicated answer-correctness scorer. First completion may precede a later query; the final scenario result still checks the last turn. Controls are scored by incompletion; this run also verifies the control wrote no entries.

## All scenarios

| Scenario | Result | Turns used | First correct ledger | First completion | Local ms | Ever erroneous entry | Final erroneous entries |
|---|---|---:|---:|---:|---:|---|---:|
| A sale and confirmation | PASS | 2 | 1 | 2 | 2.534 | No | 0 |
| Ask for an unspoken amount | PASS | 3 | 2 | 3 | 0.400 | No | 0 |
| Repair an injected wrong amount | PASS | 3 | 2 | 3 | 0.441 | Yes | 0 |
| Reject and replace a sale | PASS | 4 | 3 | 4 | 0.835 | Yes | 0 |
| Check a suspicious numeral before writing | PASS | 3 | 2 | 3 | 0.436 | No | 0 |
| Shona / English sale | PASS | 2 | 1 | 2 | 0.274 | No | 0 |
| Shona mixed-language dollars and cents | PASS | 2 | 1 | 2 | 0.252 | No | 0 |
| An unanswered question must stay unresolved | CONTROL: stayed incomplete | 1 | — | — | 0.108 | No | 0 |
| Buyer's name after the price | FAIL | 3 | 1 | — | 0.481 | Yes | 1 |
| Confirming in Yoruba (beeni) | PASS | 2 | 1 | 2 | 0.542 | No | 0 |
| Plain English question about the day | PASS | 3 | 1 | 2 | 0.505 | No | 0 |
| Yoruba question about the day | PASS | 3 | 1 | 2 | 0.522 | No | 0 |

## Complete traces

### A sale and confirmation (`direct-sale`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "rice",
    "amount": 5500,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: I sell rice for 5500 naira

Agent: Logged sale: rice, five thousand five hundred naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 2.447 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5500,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.087 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5500,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Ask for an unspoken amount (`missing-amount`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "garri",
    "amount": 5000,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: I don sell garri finish

Agent: How much did you sell the garri?

Completed: False; clarification pending: True; confirmation pending: False; erroneous active entries: 0; processing: 0.156 ms.

Ledger after turn:
```json
[]
```

**Turn 2**

Trader: five thousand

Agent: Logged sale: garri, five thousand naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.168 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "garri",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 3**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.076 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "garri",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Repair an injected wrong amount (`wrong-amount-repair`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "rice",
    "amount": 5000,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: I sell rice for 5500 naira

Agent: Logged sale: rice, five thousand five hundred naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 1; processing: 0.266 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5500,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: no no na five thousand

Agent: Corrected: rice now five thousand naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.099 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 3**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.075 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Reject and replace a sale (`reject-replace`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "rice",
    "amount": 6000,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: I sell rice for 5000 naira

Agent: Logged sale: rice, five thousand naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 1; processing: 0.275 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: no

Agent: Entry removed. What should it say? Please repeat it.

Completed: False; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.181 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "voided"
  }
]
```

**Turn 3**

Trader: I sell rice for 6000 naira

Agent: Logged sale: rice, six thousand naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.191 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "voided"
  },
  {
    "id": 2,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 6000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 4**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.188 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 5000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "voided"
  },
  {
    "id": 2,
    "type": "sale",
    "item": "rice",
    "quantity": null,
    "unit": null,
    "amount": 6000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Check a suspicious numeral before writing (`deleted-multiplier`)

Expected ledger:
```json
[
  {
    "type": "expense",
    "item": "fuel",
    "amount": 10000,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: I buy fuel thousand naira

Agent: Please check: one thousand naira for the fuel? Say 'yes' to record it, or say the correct amount.

Completed: False; clarification pending: True; confirmation pending: False; erroneous active entries: 0; processing: 0.207 ms.

Ledger after turn:
```json
[]
```

**Turn 2**

Trader: no na ten thousand

Agent: Logged expense: fuel, ten thousand naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.156 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "expense",
    "item": "fuel",
    "quantity": null,
    "unit": null,
    "amount": 10000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 3**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.074 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "expense",
    "item": "fuel",
    "quantity": null,
    "unit": null,
    "amount": 10000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Shona / English sale (`shona-sale`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "matomatisi",
    "amount": 300,
    "currency": "USD",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: Ndatengesa matomatisi ethree dollars

Agent: Logged sale: matomatisi, three dollars. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.216 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "matomatisi",
    "quantity": null,
    "unit": null,
    "amount": 300,
    "amount_each": null,
    "currency": "USD",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.058 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "matomatisi",
    "quantity": null,
    "unit": null,
    "amount": 300,
    "amount_each": null,
    "currency": "USD",
    "payment_status": "paid"
  }
]
```

### Shona mixed-language dollars and cents (`shona-mixed-price`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "rice",
    "quantity": 3,
    "unit": "cup",
    "amount": 550,
    "currency": "USD",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: Ndatengesa three cups dze rice nefive dollars fifty

Agent: Logged sale: 3 cup of rice, five dollars fifty cents. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.197 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": 3,
    "unit": "cup",
    "amount": 550,
    "amount_each": null,
    "currency": "USD",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.055 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "rice",
    "quantity": 3,
    "unit": "cup",
    "amount": 550,
    "amount_each": null,
    "currency": "USD",
    "payment_status": "paid"
  }
]
```

### An unanswered question must stay unresolved (`unanswered-question`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "garri",
    "amount": 5000,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: I don sell garri finish

Agent: How much did you sell the garri?

Completed: False; clarification pending: True; confirmation pending: False; erroneous active entries: 0; processing: 0.108 ms.

Ledger after turn:
```json
[]
```

### Buyer's name after the price (`field-buyer-name-suffix`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "biscuits",
    "amount": 220,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: i sell biscuits 220 naira for iya chinonso

Agent: Logged sale: biscuits, two hundred twenty naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.257 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "biscuits",
    "quantity": null,
    "unit": null,
    "amount": 220,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: 220 naira

Agent: What is the item? Please say its name.

Completed: False; clarification pending: True; confirmation pending: False; erroneous active entries: 0; processing: 0.151 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "biscuits",
    "quantity": null,
    "unit": null,
    "amount": 220,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 3**

Trader: yes

Agent: Logged sale: yes, two hundred twenty naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 1; processing: 0.073 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "biscuits",
    "quantity": null,
    "unit": null,
    "amount": 220,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  },
  {
    "id": 2,
    "type": "sale",
    "item": "yes",
    "quantity": null,
    "unit": null,
    "amount": 220,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Confirming in Yoruba (beeni) (`field-yoruba-confirmation`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "eyin",
    "quantity": 2,
    "unit": "crate",
    "amount": 6000,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: oya na, mo ta crate eyin meji fun 6000

Agent: Logged sale: 2 crate of eyin, six thousand naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.454 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "eyin",
    "quantity": 2,
    "unit": "crate",
    "amount": 6000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: beeni

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.088 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "eyin",
    "quantity": 2,
    "unit": "crate",
    "amount": 6000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Plain English question about the day (`field-english-sales-query`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "biscuits",
    "quantity": 3,
    "amount": 500,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: i sell 3 biscuits for 500 naira

Agent: Logged sale: 3 biscuits, five hundred naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.29 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "biscuits",
    "quantity": 3,
    "unit": null,
    "amount": 500,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.078 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "biscuits",
    "quantity": 3,
    "unit": null,
    "amount": 500,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 3**

Trader: what are my sales today

Agent: Sales today: five hundred naira from 1 sale.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.137 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "biscuits",
    "quantity": 3,
    "unit": null,
    "amount": 500,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

### Yoruba question about the day (`field-yoruba-query`)

Expected ledger:
```json
[
  {
    "type": "sale",
    "item": "isu",
    "quantity": 2,
    "amount": 6000,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 1**

Trader: oya na, mo ta isu meji fun 6000

Agent: Logged sale: 2 isu, six thousand naira. Correct?

Completed: False; clarification pending: False; confirmation pending: True; erroneous active entries: 0; processing: 0.285 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "isu",
    "quantity": 2,
    "unit": null,
    "amount": 6000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 2**

Trader: yes

Agent: Noted. Ledger correct.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.075 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "isu",
    "quantity": 2,
    "unit": null,
    "amount": 6000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

**Turn 3**

Trader: kini gbogbo oja mi leni

Agent: Your book today. Sales: isu times 2, six thousand naira. Total sales six thousand naira.

Completed: True; clarification pending: False; confirmation pending: False; erroneous active entries: 0; processing: 0.161 ms.

Ledger after turn:
```json
[
  {
    "id": 1,
    "type": "sale",
    "item": "isu",
    "quantity": 2,
    "unit": null,
    "amount": 6000,
    "amount_each": null,
    "currency": "NGN",
    "payment_status": "paid"
  }
]
```

## Limitations

- Scripted development scenarios, not held-out conversations or human participants.
- No ASR, TTS, network, LLM or user response time is included.
- Processing milliseconds measure local Python/SQLite execution only; machine dependent.
- Wrong amounts are checked after every turn, even when later repaired or voided.
- Completion requires an exact final ledger and no pending clarification or confirmation.
