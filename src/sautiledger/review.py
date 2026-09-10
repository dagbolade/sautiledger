"""Presentation data from real agent state, never inferred from reply prose."""

from __future__ import annotations

from .agent import Agent

FIELDS = ("type", "item", "quantity", "unit", "amount", "amount_each",
          "currency", "payment_status")


def transaction_review(agent: Agent) -> dict | None:
    if agent.pending is not None:
        pending = agent.pending.to_dict()
        return {
            "status": "not_recorded",
            "question_about": pending.get("question_about"),
            "transaction": {key: pending.get(key) for key in FIELDS},
        }
    if agent.awaiting_confirm and agent.last_logged_id is not None:
        row = agent.ledger.last_transaction()
        if row is not None and row["id"] == agent.last_logged_id:
            return {
                "status": "recorded_awaiting_confirmation",
                "question_about": "recorded_entry",
                "transaction": {key: row[key] for key in FIELDS},
            }
    return None
