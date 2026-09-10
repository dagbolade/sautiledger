"""Deterministic English rendering of legacy Pidgin reply templates.

Only full templates match; captured item names and monetary values are untouched.
No translation service, model call, or new ledger operation is involved.
"""
import re

_TEMPLATES = [
    (r"How much you sell am\?", "What was the total amount?"),
    (r"Wetin you want make I log\? Tell me the item and the amount, abeg\.", "What would you like to record? Tell me the item and amount."),
    (r"Wetin she buy\? Talk the thing name\.", "What is the item? Please say its name."),
    (r"How much you (.+)\?", r"How much did you \1?"),
    (r"I don remove am\. Wetin I write wrong\? Talk am again\.", "Entry removed. What should it say? Please repeat it."),
    (r"Oya talk am again make I hear well\.", "Please repeat the item and amount."),
    (r"Wetin I hear no clear at all, so I no write anything\. Abeg talk am again — just the item and the amount\.", "I could not understand that, so nothing was recorded. Please repeat just the item and amount."),
    (r"Na (.+) you talk\?", r"Did you say \1?"),
    (r"Make I sure first — na (.+)\? Talk 'yes' make I write am, or talk the correct amount\.", r"Please check: \1? Say 'yes' to record it, or say the correct amount."),
    (r"Na (.+) naira for each one, or (.+) naira for everything\?", r"Is that \1 naira each, or \2 naira in total?"),
    (r"I hear (.+) naira — that number get strange shape\. Abeg talk the amount one more time make I sure\.", r"I heard \1 naira. Please repeat the amount so I can check it."),
    (r"I don note am\. The entry still stand: (.+)\. If something wrong, talk 'no, na …' make I fix am\.", r"Note saved. The entry remains: \1. To correct it, say 'no' followed by the correct details."),
    (r"You never sell (.+)\.", r"No sales recorded for \1."),
    (r"Your best seller (.+) na (.+), (.+)\.", r"Your best seller \1 is \2, \3."),
    (r"Nobody dey owe you\. Credit book clean\.", "No outstanding credit."),
    (r"Nothing don enter the book (.+) yet\.", r"No entries recorded \1 yet."),
    (r"You sell (.+), you spend (.+) — you don spend pass sales by (.+) o\.", r"Sales: \1. Expenses: \2. Expenses exceed sales by \3."),
    (r"You sell (.+), you spend (.+) — wetin remain na (.+)\.", r"Sales: \1. Expenses: \2. Sales less expenses: \3."),
    (r"(.+) you never make anything o — (.+) in sales but (.+) spend: you dey down (.+)\.", r"\1: \2 in sales, \3 in expenses. Expenses exceed sales by \4."),
    (r"You don make (.+) (today|yesterday|this week) — (.+) in sales, (.+) spend\.", r"Sales less expenses \2: \1. Sales: \3. Expenses: \4."),
    (r"You don make (.+) from (.+)\.", r"Sales: \1 from \2."),
    (r"Noted: last entry na (.+), she go pay (.+)\. I dey watch am\.", r"Last entry marked \1. Payment due \2."),
    (r"Noted: last entry na (.+)\. I dey watch am\.", r"Last entry marked \1."),
    (r"Book empty for today\. Nothing don enter yet\.", "Your book is empty today. No entries yet."),
    (r"Voice don reach im limit for today o\. Type am instead, abeg\.", "Today's voice limit has been reached. You can still type your entry."),
    (r"I no hear you well, abeg (?:try again|talk am again)\.", "I could not hear you clearly. Please try again."),
    (r"Network wahala — I no fit reach the cloud right now\. Try again small time\.", "The voice service is unavailable. Please try again or type your entry."),
]


def english_reply(reply: str) -> str:
    for pattern, replacement in _TEMPLATES:
        if re.fullmatch(pattern, reply):
            return re.sub(pattern, replacement, reply)
    # Recaps are composed from fixed labels and verbatim ledger fields.
    if reply.startswith("Your book today. "):
        return (reply.replace("Money wey enter: ", "Sales: ")
                .replace("Money wey comot: ", "Expenses: ")
                .replace("wetin remain na ", "sales less expenses: ")
                .replace(" — you don spend pass sales o", " — expenses exceed sales"))
    return reply
