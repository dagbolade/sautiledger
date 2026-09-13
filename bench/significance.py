"""How sure are we? Paired significance tests on the headline comparisons.

python -m bench.significance

Every comparison is PAIRED (same clips, two systems), which is the right
design when each clip is heard by every model. Two tests per comparison:

  * a percentile bootstrap 95% confidence interval on the mean per-clip
    difference (20,000 resamples, fixed seed, so the output is reproducible);
  * an exact two-sided sign test (transcription metrics) or exact McNemar
    test (binary transaction metrics) on the clips where the systems differ.

A difference is called SIGNIFICANT only when the interval excludes zero AND
p < 0.05. With 15 clips per native tier, many real differences will not
reach that bar; "not significant" means "not shown", not "equal".
"""

from __future__ import annotations

import json
import random
from math import comb
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results" / "metrics.json"
AFX_MANIFEST = Path(__file__).resolve().parent / "corpus" / "afriswitch-sample" / "manifest.jsonl"

COMPARISONS = [
    # (group, metric, system A, system B)
    ("sautiledger-clips", "exact_match", "mai-transcribe-2", "sahara-v2.5"),
    ("sautiledger-clips", "exact_match", "gpt-4o-transcribe", "sahara-v2.5"),
    ("sh-clips", "exact_match", "sahara-v2.5", "mai-transcribe-2"),
    ("sh-clips", "amount_corrupted", "mai-transcribe-2", "sahara-v2.5"),
    ("sautiledger-clips", "wer", "sahara-v2.5", "mai-transcribe-2"),
    ("sautiledger-clips", "wer", "sahara-v2.5", "gpt-4o-transcribe"),
    ("sautiledger-clips", "wer", "sahara-v2.5", "whisper-large-v3"),
    ("sh-clips", "wer", "sahara-v2.5", "mai-transcribe-2"),
    ("sh-clips", "wer", "sahara-v2.5", "gpt-4o-transcribe"),
    ("sh-clips", "wer", "sahara-v2.5", "parakeet-tdt"),
    ("sh-clips", "wer", "sahara-v2.5", "chirp-3"),
    ("sh-clips", "wer", "sahara-v2.5", "whisper-large-v3"),
    ("sh-clips", "wer", "sahara-v2.5", "omnilingual-ctc-300m"),
    ("afriswitch-sample", "wer", "sahara-v2.5", "chirp-3"),
    ("afriswitch-sample", "wer", "sahara-v2.5", "mai-transcribe-2"),
    ("afx-yoruba", "wer", "chirp-3", "sahara-v2.5"),
    ("afx-hausa", "wer", "chirp-3", "sahara-v2.5"),
]

BINARY = {"exact_match", "amount_safe", "amount_corrupted", "numeric_accuracy"}


def _groups() -> dict[str, str]:
    if not AFX_MANIFEST.exists():
        return {}
    return {json.loads(line)["id"]: "afx-" + json.loads(line)["source_config"]
            for line in AFX_MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()}


def _values(rows, model, group, metric, afx):
    out = {}
    for r in rows:
        if r["model"] != model:
            continue
        g = afx.get(r["clip"]) if group.startswith("afx-") else r["tier"]
        if g == group and r.get(metric) is not None:
            out[r["clip"]] = float(r[metric])
    return out


def _exact_two_sided(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def compare(rows, group, metric, a, b, afx, resamples=20000, seed=2026):
    va, vb = _values(rows, a, group, metric, afx), _values(rows, b, group, metric, afx)
    clips = sorted(set(va) & set(vb))
    diffs = [va[c] - vb[c] for c in clips]
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(resamples))
    lo, hi = boots[int(0.025 * resamples)], boots[int(0.975 * resamples)]
    a_higher = sum(d > 0 for d in diffs)
    b_higher = sum(d < 0 for d in diffs)
    p = _exact_two_sided(a_higher, a_higher + b_higher)
    excludes_zero = lo > 0 or hi < 0
    return {
        "group": group, "metric": metric, "a": a, "b": b, "n": len(clips),
        "mean_a": sum(va[c] for c in clips) / len(clips),
        "mean_b": sum(vb[c] for c in clips) / len(clips),
        "diff": sum(diffs) / len(diffs), "ci95": [lo, hi],
        "clips_a_higher": a_higher, "clips_b_higher": b_higher,
        "test": "McNemar (exact)" if metric in BINARY else "sign test (exact)",
        "p": p, "significant": excludes_zero and p < 0.05,
        "verdict": ("significant" if excludes_zero and p < 0.05
                    else "interval excludes zero, test not significant" if excludes_zero
                    else "not significant"),
    }


def main() -> None:
    rows = json.loads(RESULTS.read_text(encoding="utf-8"))["results"]
    afx = _groups()
    for group, metric, a, b in COMPARISONS:
        if group.startswith("afx-") and not afx:
            print(f"{group}: skipped (AfriSwitch manifest not present)")
            continue
        r = compare(rows, group, metric, a, b, afx)
        pct = metric in BINARY
        fmt = (lambda x: f"{x:+.0%}") if pct else (lambda x: f"{x:+.3f}")
        print(f"{group:18} {metric:16} {a} vs {b}: n={r['n']:2} "
              f"diff {fmt(r['diff'])} CI [{fmt(r['ci95'][0])}, {fmt(r['ci95'][1])}] "
              f"clips {r['clips_a_higher']}-{r['clips_b_higher']} p={r['p']:.3f} -> {r['verdict']}")


if __name__ == "__main__":
    main()
