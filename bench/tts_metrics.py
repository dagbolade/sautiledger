"""TTS round-trip metrics.

Intron's guidance (WhatsApp, 9 Sep) asks TTS submissions to report
Hallucination, Transcript loss, Segment loss, WER and Accuracy. The paper
they cite (Rai et al., ASR-FairBench, Interspeech 2025) defines none of
these — it is an ASR *fairness* benchmark — so each metric is defined
here, explicitly, and the report states these definitions.

Method: round-trip (no human listeners). Text -> TTS -> audio -> a
NEUTRAL third-party ASR -> transcript, then compare transcript to the
input text. Every metric derives from one word-level alignment.

  WER             (S+D+I)/N  — the standard rate
  Accuracy        1.0 if the normalised transcript matches exactly
  Transcript loss D/N        — input words that vanished
  Hallucination   I/N        — words that appeared from nowhere
  Segment loss    longest contiguous deletion run / N — a dropped PHRASE
                  (truncated audio), which D/N alone hides
  Amount survival did the money figure survive? — the product metric:
                  a readback is a safety device, so a lost or altered
                  amount is a failure even at low WER
"""

from __future__ import annotations

from .metrics import derivable_numbers, normalize_text
from sautiledger.packs import Pack


def _align(ref: list[str], hyp: list[str]) -> list[str]:
    """Levenshtein backtrace -> ops in reference order: '=', 'S', 'D', 'I'."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    ops: list[str] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            ops.append("=" if ref[i - 1] == hyp[j - 1] else "S")
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append("D")
            i -= 1
        else:
            ops.append("I")
            j -= 1
    return list(reversed(ops))


def _longest_run(ops: list[str], kind: str) -> int:
    best = run = 0
    for op in ops:
        run = run + 1 if op == kind else 0
        best = max(best, run)
    return best


def score_roundtrip(text: str, transcript: str, pack: Pack,
                    expected_amount: int | None = None) -> dict:
    ref = normalize_text(text)
    hyp = normalize_text(transcript)
    if not ref:
        return {}
    ops = _align(ref, hyp)
    subs = ops.count("S")
    dels = ops.count("D")
    ins = ops.count("I")
    n = len(ref)

    amount_survived = None
    if expected_amount is not None:
        amount_survived = expected_amount in derivable_numbers(transcript, pack)

    return {
        "wer": round((subs + dels + ins) / n, 4),
        "accuracy": 1.0 if ref == hyp else 0.0,
        "transcript_loss": round(dels / n, 4),
        "hallucination": round(ins / n, 4),
        "segment_loss": round(_longest_run(ops, "D") / n, 4),
        # a dropped phrase, not just scattered words
        "segment_dropped": _longest_run(ops, "D") >= 3,
        "amount_survived": amount_survived,
        "n_ref_words": n,
    }
