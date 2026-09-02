"""sh-ZW cases from normaliser_tests_sh.json — the native-corrected Shona
tier (2026-09-02). Same bar as the frozen spec: exact structural match,
grammar-only (the LLM raises if consulted). Never weaken; if a case looks
wrong, the fix is a conversation with the native speaker, not an edit here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sautiledger.normaliser import normalise
from sautiledger.packs import load_pack
from sautiledger.tools import _money

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "normaliser_tests_sh.json").read_text(encoding="utf-8"))


class RaisingLlm:
    def complete(self, prompt: str) -> str:
        raise AssertionError("LLM fallback consulted on a grammar-only case")


@pytest.fixture(scope="module")
def pack():
    return load_pack("sh-ZW")


@pytest.mark.parametrize("case", SPEC["cases"], ids=lambda c: f"sh{c['id']}")
def test_case(case, pack):
    result = normalise(case["utterance"], pack, llm=RaisingLlm())
    got = result.to_dict()
    for key, expected in case["expect"].items():
        assert got.get(key) == expected, (
            f"sh case {case['id']} ({case['utterance']!r}): "
            f"{key}={got.get(key)!r}, expected {expected!r}"
        )


def test_clarify_cases_never_carry_an_amount(pack):
    for case in SPEC["cases"]:
        if case["expect"]["intent"] != "clarify":
            continue
        result = normalise(case["utterance"], pack, llm=RaisingLlm())
        assert result.amount is None, f"sh case {case['id']} guessed an amount"


def test_usd_readback_renders_cents():
    """The confirm the trader hears must say $5.50, never 'five hundred fifty'."""
    assert _money(550, "USD") == "five dollars fifty cents"
    assert _money(4500, "USD") == "forty five dollars"
    assert _money(150, "USD") == "one dollar fifty cents"
    assert _money(100, "USD") == "one dollar"
    assert _money(250, "USD") == "two dollars fifty cents"


def test_glued_prefix_never_splits_real_words(pack):
    """'enzungu' (e + nzungu) must survive — the split fires only when the
    remainder is a known number/currency word."""
    from sautiledger.normaliser import _split_glued
    assert _split_glued(["enzungu", "nefive", "yeten", "ethree", "neone"], pack) == \
        ["enzungu", "five", "ten", "three", "one"]


def test_dollars_alone_is_unparseable(pack):
    """A bare currency word carries no amount — clarify, never guess."""
    result = normalise("ndatengesa shuga dollars", pack, llm=RaisingLlm())
    assert result.intent == "clarify"
    assert result.amount is None


def test_major_word_rules_are_pack_gated():
    """pcm-yo-NG has no major_unit_words — 'dollars' must not become money."""
    pcm = load_pack("pcm-yo-NG")
    result = normalise("I don sell garri five dollars fifty", pcm, llm=RaisingLlm())
    assert result.amount != 550  # the cents rule must not leak across packs
