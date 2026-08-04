"""Benchmark metrics. Pure functions, no ASR dependencies — unit-testable
without any model installed.

WER normalisation: the Intron-Multimodal-Benchmarking repo reports
normalised + unnormalised WER but does not publish its normaliser, so we
use jiwer-standard conventions (lowercase, strip punctuation, collapse
whitespace) and state that in the report. We mirror their dual convention
by reporting both raw and normalised WER.

The centrepiece is TRANSACTION ACCURACY: each model's raw transcript is
fed through OUR normaliser and the resulting ParseResult compared to the
expected parse at three levels — exact_match, amount_safe (correct OR
clarify: asking is safe), amount_corrupted (a WRONG amount would have
been written to someone's money records — the failure that matters).
"""

from __future__ import annotations

import re

from sautiledger.normaliser import is_moneyish, normalise, parse_money, tokenize
from sautiledger.packs import Pack

# ---------------------------------------------------------------- WER


def normalize_text(text: str) -> list[str]:
    """jiwer-standard: lowercase, strip punctuation (apostrophes too, so
    "don't" -> "dont"), collapse whitespace."""
    return re.findall(r"[a-z0-9]+", text.lower().replace("'", ""))


def wer(truth: str, hyp: str, normalized: bool = True) -> float:
    """Word error rate (S+D+I)/N via word-level edit distance."""
    ref = normalize_text(truth) if normalized else truth.split()
    hyp_words = normalize_text(hyp) if normalized else hyp.split()
    if not ref:
        return 0.0 if not hyp_words else 1.0
    prev = list(range(len(hyp_words) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp_words)
        for j, h in enumerate(hyp_words, 1):
            cur[j] = min(
                prev[j] + 1,          # deletion
                cur[j - 1] + 1,       # insertion
                prev[j - 1] + (r != h),  # substitution
            )
        prev = cur
    return prev[-1] / len(ref)


# ---------------------------------------------------------------- numbers


def derivable_numbers(text: str, pack: Pack) -> set[int]:
    """Every monetary/quantity value recoverable from a transcript:
    digit forms ("5500", "3"), k-forms ("5k", "5.5k"), single number
    words, and every pack money pattern over contiguous money-token runs
    ("five k five" -> 5500, "egberun meta" -> 3000)."""
    values: set[int] = set()
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*k\b", text.lower()):
        values.add(int(float(m.group(1)) * 1000))
    tokens = tokenize(text)
    for tok in tokens:
        if tok.isdigit():
            values.add(int(tok))
        if tok in pack.numbers:
            values.add(pack.numbers[tok])
    # money patterns over every contiguous run of money-ish tokens
    run: list[str] = []
    for tok in tokens + ["<end>"]:
        if tok != "<end>" and is_moneyish(tok, pack):
            run.append(tok)
            continue
        for start in range(len(run)):
            for end in range(start + 1, len(run) + 1):
                result = parse_money(run[start:end], None, pack)
                if isinstance(result, dict):
                    values |= {v for v in (result.get("amount"), result.get("amount_each")) if v}
        run = []
    return values


def expected_numbers(expected_parse: dict) -> list[int]:
    keys = ["amount", "amount_each", "quantity"]
    if isinstance(expected_parse.get("amount_each"), int):
        # per-unit pricing: the total is derived (each × qty), never spoken
        keys.remove("amount")
    if expected_parse.get("field") == "amount":
        keys.append("new_value")
    return [expected_parse[k] for k in keys if isinstance(expected_parse.get(k), int)]


def numeric_accuracy(expected_parse: dict, hyp_text: str, pack: Pack) -> bool:
    """Did every monetary amount and quantity survive transcription?"""
    needed = expected_numbers(expected_parse)
    if not needed:
        return True
    available = derivable_numbers(hyp_text, pack)
    return all(n in available for n in needed)


# ---------------------------------------------------------------- flags

_INVERSION_PAIRS = [("don sell", "dont sell"), ("don buy", "dont buy"), ("don make", "dont make")]


def transcription_flags(truth: str, hyp: str) -> list[str]:
    """Meaning-changing error classes worth surfacing in the report."""
    flags = []
    t = " ".join(normalize_text(truth))
    h = " ".join(normalize_text(hyp))
    for perfective, negation in _INVERSION_PAIRS:
        if perfective in t and negation in h:
            flags.append("perfective_negation_inversion")
            break
    return flags


# ---------------------------------------------------------------- transaction accuracy


def transaction_metrics(expected_parse: dict, hyp_text: str, pack: Pack) -> dict:
    """Feed the model's transcript through OUR normaliser (grammar-only,
    exactly as the app runs it) and score the outcome."""
    got = normalise(hyp_text, pack, llm=None).to_dict()

    exact = all(got.get(k) == v for k, v in expected_parse.items())

    expected_intent = expected_parse.get("intent")
    exp_amount = expected_parse.get("amount")
    exp_each = expected_parse.get("amount_each")

    if got["intent"] == "clarify":
        # Asking is always safe — nothing gets written.
        amount_safe, amount_corrupted = True, False
    elif expected_intent == "clarify":
        # Truth demanded a question; the mangled transcript let an entry
        # through without asking. Whatever it logged, it guessed.
        amount_safe, amount_corrupted = False, got.get("amount") is not None
    elif got.get("amount") is not None or got.get("new_value") is not None:
        correct = got.get("amount") == exp_amount and got.get("amount_each") == exp_each
        if expected_parse.get("field") == "amount":
            correct = got.get("new_value") == expected_parse.get("new_value")
        amount_safe, amount_corrupted = correct, not correct
    else:
        # No amount produced (e.g. parsed as a query): nothing wrong was
        # written, but nothing correct either.
        amount_safe, amount_corrupted = exp_amount is None and exp_each is None, False

    return {
        "exact_match": exact,
        "amount_safe": amount_safe,
        "amount_corrupted": amount_corrupted,
        "got_intent": got["intent"],
        "got_amount": got.get("amount"),
    }


def score_clip(truth: str, hyp: str, expected_parse: dict, pack: Pack) -> dict:
    return {
        "wer": round(wer(truth, hyp), 4),
        "wer_raw": round(wer(truth, hyp, normalized=False), 4),
        "numeric_accuracy": numeric_accuracy(expected_parse, hyp, pack),
        "flags": transcription_flags(truth, hyp),
        **transaction_metrics(expected_parse, hyp, pack),
    }
