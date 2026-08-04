"""Runs every case in normaliser_tests.json — the source of truth.

acceptance_rules enforcement:
- Exact structural match on every key the case's expect block declares.
- The spec requires grammar-only for cases 1-3, 5, 7-13; our packs cover
  all 20 cases, so we hold every case to the stricter bar: the LLM
  client raises if it is ever consulted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sautiledger.normaliser import normalise
from sautiledger.packs import load_pack

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "normaliser_tests.json").read_text(encoding="utf-8"))


class RaisingLlm:
    def complete(self, prompt: str) -> str:
        raise AssertionError("LLM fallback consulted on a grammar case (rule 4 violation)")


@pytest.fixture(scope="module")
def packs():
    return {name: load_pack(name) for name in SPEC["packs"]}


@pytest.mark.parametrize("case", SPEC["cases"], ids=lambda c: f"case{c['id']}")
def test_case(case, packs):
    result = normalise(case["utterance"], packs[case["pack"]], llm=RaisingLlm())
    got = result.to_dict()
    for key, expected in case["expect"].items():
        assert got.get(key) == expected, (
            f"case {case['id']} ({case['utterance']!r}): "
            f"{key}={got.get(key)!r}, expected {expected!r}"
        )


def test_clarify_cases_never_carry_an_amount(packs):
    """Cases 4, 6, 20 must clarify — and must not smuggle a guessed amount."""
    for case in SPEC["cases"]:
        if case["expect"]["intent"] != "clarify":
            continue
        result = normalise(case["utterance"], packs[case["pack"]], llm=RaisingLlm())
        assert result.intent == "clarify", f"case {case['id']} must clarify"
        assert result.amount is None, f"case {case['id']} guessed an amount"
