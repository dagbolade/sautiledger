"""Unit tests for the benchmark metric functions — synthetic cases only,
no audio, no models."""

from __future__ import annotations

from bench.metrics import (
    derivable_numbers,
    numeric_accuracy,
    score_clip,
    transaction_metrics,
    transcription_flags,
    wer,
)
from sautiledger.packs import load_pack

PACK = load_pack("pcm-yo-NG")

TRUTH = "I don sell three bags of rice five thousand five"
EXPECTED = {
    "intent": "log_transaction",
    "type": "sale",
    "item": "rice",
    "quantity": 3,
    "unit": "bag",
    "amount": 5500,
    "currency": "NGN",
}


def test_wer_identical_is_zero():
    assert wer(TRUTH, TRUTH) == 0.0


def test_wer_normalisation_forgives_case_and_punct():
    assert wer("Sell rice, five K!", "sell rice five k") == 0.0


def test_derivable_numbers_handles_all_formats():
    values = derivable_numbers("I dont sell 3 bags 5.5k", PACK)
    assert 5500 in values and 3 in values
    values = derivable_numbers("sell garri egberun meta", PACK)
    assert 3000 in values


def test_the_inversion_case():
    """Canonical synthetic case: 'I dont sell 3 bags 5.5k' vs truth
    'I don sell three bags five thousand five' — numeric-accurate, but flagged."""
    hyp = "I dont sell 3 bags of rice 5.5k"
    assert numeric_accuracy(EXPECTED, hyp, PACK) is True
    assert "perfective_negation_inversion" in transcription_flags(TRUTH, hyp)


def test_transaction_metrics_correct_transcript():
    result = transaction_metrics(EXPECTED, "I don sell three bags of rice five thousand five", PACK)
    assert result["exact_match"] and result["amount_safe"] and not result["amount_corrupted"]


def test_transaction_metrics_corrupted_amount():
    # transcription mangled "five thousand five" (5500) into "five k" (5000):
    # the normaliser confidently logs the WRONG amount — the failure that matters
    result = transaction_metrics(EXPECTED, "I don sell three bags of rice five k", PACK)
    assert result["amount_corrupted"] and not result["amount_safe"]


def test_transaction_metrics_clarify_is_safe():
    # a garbled amount that the grammar refuses to value → clarify → safe
    result = transaction_metrics(EXPECTED, "I don sell three bags of rice egbeje owo", PACK)
    assert result["got_intent"] == "clarify"
    assert result["amount_safe"] and not result["amount_corrupted"]


def test_guessing_through_an_expected_clarify_is_corrupted():
    expected_clarify = {"intent": "clarify", "question_about": "amount"}
    # transcript that "resolves" the ambiguity the truth says must be asked about
    result = transaction_metrics(expected_clarify, "customer take two paint rubber of garri two fifty", PACK)
    if result["got_amount"] is not None:
        assert result["amount_corrupted"]


def test_score_clip_shape():
    row = score_clip(TRUTH, "I dont sell 3 bags of rice 5.5k", EXPECTED, PACK)
    assert set(row) >= {
        "wer", "wer_raw", "numeric_accuracy", "flags",
        "exact_match", "amount_safe", "amount_corrupted",
    }
    assert row["numeric_accuracy"] is True
    assert row["flags"] == ["perfective_negation_inversion"]
