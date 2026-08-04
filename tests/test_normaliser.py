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


class _Reduplication:
    """Native-speaker rule: doubled money = distributive (per-unit price)."""


def test_reduplication_full_phrase_doubling(packs):
    result = normalise(
        "customer take two paint rubber of garri two fifty two fifty",
        packs["pcm-yo-NG"], llm=RaisingLlm(),
    )
    assert result.intent == "log_transaction"
    assert result.amount_each == 250 and result.amount == 500


def test_reduplication_bare_double(packs):
    result = normalise(
        "sell three congo of garri hundred hundred", packs["pcm-yo-NG"], llm=RaisingLlm()
    )
    assert result.intent == "log_transaction"
    assert result.amount_each == 100 and result.amount == 300


def test_reduplication_leading_token(packs):
    result = normalise(
        "customer take two mudu of elubo one one thousand", packs["pcm-yo-NG"], llm=RaisingLlm()
    )
    assert result.intent == "log_transaction"
    assert result.amount_each == 1000 and result.amount == 2000


def test_reduplication_is_pack_gated(packs):
    """sw-KE has NOT validated this rule — same shape must not distribute."""
    result = normalise("nimeuza mahindi gunia mbili mia tano mia tano", packs["sw-KE"], llm=RaisingLlm())
    assert result.amount_each is None  # no distributive without the pack flag


def test_clarify_cases_never_carry_an_amount(packs):
    """Cases 4, 6, 20 must clarify — and must not smuggle a guessed amount."""
    for case in SPEC["cases"]:
        if case["expect"]["intent"] != "clarify":
            continue
        result = normalise(case["utterance"], packs[case["pack"]], llm=RaisingLlm())
        assert result.intent == "clarify", f"case {case['id']} must clarify"
        assert result.amount is None, f"case {case['id']} guessed an amount"
