"""Replay scripted conversations through the actual agent and SQLite ledger.

python -m bench.conversations

No audio recognition, synthesis, local LLM, user wait time or remote calls.
Results are a development evaluation, not a human task-completion study.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack
from sautiledger.review import FIELDS, transaction_review
from sautiledger.replies import english_reply

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = Path(__file__).with_name("conversation_scenarios.json")


def ledger_snapshot(ledger: Ledger) -> list[dict]:
    return [{"id": row["id"], **{key: row[key] for key in FIELDS}}
            for row in ledger.all_transactions()]


def exact_ledger(rows: list[dict], expected: list[dict]) -> bool:
    active = [row for row in rows if row["payment_status"] != "voided"]
    return len(active) == len(expected) and all(
        all(row.get(key) == value for key, value in target.items())
        for row, target in zip(active, expected)
    )


def wrong_amount_count(rows: list[dict], expected: list[dict]) -> int:
    """Count unmatched active monetary entries, including extra duplicates.

    Each target can justify one row with that type/currency/amount. This
    is amount-only; field-level errors are exposed separately by exact_ledger.
    """
    targets = Counter((r.get("type"), r.get("currency"), r.get("amount")) for r in expected)
    wrong = 0
    for row in rows:
        if row["payment_status"] == "voided":
            continue
        key = (row.get("type"), row.get("currency"), row.get("amount"))
        if targets[key]:
            targets[key] -= 1
        else:
            wrong += 1
    return wrong


def run_scenario(scenario: dict) -> dict:
    ledger = Ledger(":memory:")
    agent = Agent(load_pack(scenario["pack"]), ledger, llm=None)
    trace = []
    first_correct_turn = None
    first_completed_turn = None
    elapsed_ms = 0.0
    try:
        for index, text in enumerate(scenario["turns"], 1):
            before = ledger_snapshot(ledger)
            start = perf_counter()
            reply = english_reply(agent.handle(text))
            duration = (perf_counter() - start) * 1000
            elapsed_ms += duration
            after = ledger_snapshot(ledger)
            exact = exact_ledger(after, scenario["expected"])
            needs_response = agent.pending is not None or agent.awaiting_confirm or "?" in reply
            complete = exact and not needs_response
            if exact and first_correct_turn is None:
                first_correct_turn = index
            if complete and first_completed_turn is None:
                first_completed_turn = index
            trace.append({
                "turn": index, "input": text, "reply": reply,
                "processing_ms": round(duration, 3),
                "before": before, "after": after,
                "exact_ledger": exact, "completed": complete,
                "clarification_pending": agent.pending is not None,
                "confirmation_pending": agent.awaiting_confirm,
                "wrong_amounts_active": wrong_amount_count(after, scenario["expected"]),
                "review": transaction_review(agent),
            })
        final = trace[-1]
        return {
            **scenario, "trace": trace,
            "completed": final["completed"], "final_ledger_exact": final["exact_ledger"],
            "first_correct_turn": first_correct_turn,
            "first_completed_turn": first_completed_turn,
            "turns_used": len(trace),
            "clarification_turns": sum(t["clarification_pending"] for t in trace),
            "ever_committed_wrong_amount": any(t["wrong_amounts_active"] for t in trace),
            "final_wrong_amounts": final["wrong_amounts_active"],
            "local_processing_ms": round(elapsed_ms, 3),
        }
    finally:
        ledger.conn.close()


def evaluate(source: Path = DEFAULT_SCENARIOS) -> dict:
    spec = json.loads(source.read_text(encoding="utf-8"))
    scenarios = spec["scenarios"]
    if not scenarios or any(not s.get("turns") for s in scenarios):
        raise ValueError("Each scenario needs at least one input turn")
    if len({s["id"] for s in scenarios}) != len(scenarios):
        raise ValueError("Scenario IDs must be unique")
    results = [run_scenario(s) for s in scenarios]
    # Fingerprint the actual measured code and language packs, not just fixtures.
    implementation = hashlib.sha256()
    for file in sorted((ROOT / "src/sautiledger").glob("*.py")) + sorted((ROOT / "packs").glob("*.yaml")):
        implementation.update(file.relative_to(ROOT).as_posix().encode())
        implementation.update(file.read_bytes())
    completed = [r for r in results if r["completed"]]
    return {
        "schema_version": 1,
        "evaluation_kind": "scripted_transcript_replay",
        "provenance": spec["provenance"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenarios_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "implementation_sha256": implementation.hexdigest(),
        "limitations": [
            "Scripted development scenarios, not held-out conversations or human participants.",
            "No ASR, TTS, network, LLM or user response time is included.",
            "Processing milliseconds measure local Python/SQLite execution only; machine dependent.",
            "Wrong amounts are checked after every turn, even when later repaired or voided.",
            "Completion requires an exact final ledger and no pending clarification or confirmation.",
        ],
        "summary": {
            "scenarios": len(results), "completed": len(completed),
            "completion_rate": len(completed) / len(results),
            "median_turns_to_completion": statistics.median(r["first_completed_turn"] for r in completed) if completed else None,
            "scenarios_with_wrong_amount_at_any_turn": sum(r["ever_committed_wrong_amount"] for r in results),
            "scenarios_with_wrong_final_amount": sum(bool(r["final_wrong_amounts"]) for r in results),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=ROOT / "bench/results/conversations.json")
    args = parser.parse_args()
    report = evaluate(args.scenarios)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Scripted replay results: {args.output}")


if __name__ == "__main__":
    main()
