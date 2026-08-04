"""Renders bench/results/REPORT.md from metrics.json."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"

PROS_CONS = {
    "sahara-v2": (
        "Built for exactly this speech: code-switched African utterances, dense "
        "numbers, market vocabulary. Cloud-only in this benchmark (offline "
        "deployment exists but was not under test); every call is visible in the "
        "egress ledger. Judged here on downstream safety, not just WER."
    ),
    "whisper-large-v3": (
        "Strong general-purpose local model; runs fully offline. Known weaknesses "
        "on Pidgin and Yoruba numerals; tends to 'anglicise' code-switched speech, "
        "which is precisely the error class that corrupts amounts downstream."
    ),
    "whisper-small": (
        "Lightweight local substitute (used only when no frontier API key was "
        "available). Fast and offline, but weakest on accented, code-switched "
        "speech — treat its numbers as a floor, not a fair frontier baseline."
    ),
    "gpt-4o-transcribe": (
        "Frontier multimodal ASR; strong on clean accented English. Unknown "
        "training exposure to Pidgin/Yoruba market speech; per-call cost and "
        "cloud-only operation make it a poor fit for the sovereignty story even "
        "where accuracy competes."
    ),
    "gemini-flash": (
        "Frontier multimodal model with audio input; competitive on accented "
        "English. Same caveats as other frontier APIs: cloud-only, and transcript "
        "phrasing can drift toward standard English, breaking Pidgin grammar cues."
    ),
}


def _pct(values: list[bool | float]) -> str:
    if not values:
        return "–"
    if isinstance(values[0], bool):
        return f"{100 * sum(values) / len(values):.0f}%"
    return f"{100 * sum(values) / len(values):.1f}%"


def render() -> Path:
    data = json.loads((RESULTS_DIR / "metrics.json").read_text(encoding="utf-8"))
    rows = data["results"]
    by_tier_model: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        by_tier_model[(row["tier"], row["model"])].append(row)

    lines: list[str] = []
    add = lines.append
    add("# SautiLedger ASR Benchmark Report")
    add("")
    add(f"Corpus frozen before first run — manifest sha256: `{data['manifest_sha256']}`.")
    add(f"Clips scored: {data['n_clips']} (missing/skipped: {data['n_missing']}).")
    for note in data.get("notes", []):
        add(f"> **Note:** {note}")
    add("")

    add("## Summary")
    add("")
    tiers = sorted({t for t, _ in by_tier_model})
    for tier in tiers:
        add(f"### Corpus tier: `{tier}`")
        add("")
        add("| Model | WER (norm) | WER (raw) | Numeric acc | Txn exact | Amount safe | **Amount corrupted** |")
        add("|---|---|---|---|---|---|---|")
        for (t, model), group in sorted(by_tier_model.items()):
            if t != tier:
                continue
            add(
                f"| {model} | {_pct([r['wer'] for r in group])} | {_pct([r['wer_raw'] for r in group])} "
                f"| {_pct([r['numeric_accuracy'] for r in group])} | {_pct([r['exact_match'] for r in group])} "
                f"| {_pct([r['amount_safe'] for r in group])} | **{_pct([r['amount_corrupted'] for r in group])}** |"
            )
        add("")

    add("The three-level transaction metric is the point: WER alone understates the")
    add("differences for financial use. *Amount corrupted* counts transcripts that made")
    add("our normaliser log a WRONG amount — the failure a market trader cannot afford.")
    add("*Amount safe* includes clarify outcomes: an agent that asks is safe, an agent")
    add("that guesses is not. Transcription accuracy is necessary but not sufficient for")
    add("financial records; the grammar-first normaliser + clarify design is the safety")
    add("layer, and the amount-corrupted column is the evidence of what it repairs.")
    add("")

    add("## Illustrative examples")
    add("")
    by_clip: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_clip[row["clip"]].append(row)
    scored = sorted(
        by_clip.items(),
        key=lambda kv: -(max(r["wer"] for r in kv[1]) - min(r["wer"] for r in kv[1])),
    )
    flagged = [kv for kv in by_clip.items() if any(r["flags"] for r in kv[1])]
    examples = (flagged + [kv for kv in scored if kv not in flagged])[:5]
    for clip_id, group in examples:
        add(f"**{clip_id}** — truth: `{group[0]['truth']}`")
        add("")
        for row in sorted(group, key=lambda r: r["model"]):
            flags = f"  ⚠ {', '.join(row['flags'])}" if row["flags"] else ""
            corrupted = "  ✗ AMOUNT CORRUPTED" if row["amount_corrupted"] else ""
            add(f"- `{row['model']}`: `{row['hyp']}`{flags}{corrupted}")
        add("")

    add("## Per-model notes")
    add("")
    for model in sorted({m for _, m in by_tier_model}):
        add(f"**{model}** — {PROS_CONS.get(model, 'No notes.')}")
        add("")

    add("## Methodology & caveats")
    add("")
    add("- WER: word-level (S+D+I)/N. Normalised = lowercase, punctuation stripped,")
    add("  whitespace collapsed (jiwer-standard). The Intron-Multimodal-Benchmarking")
    add("  repo reports normalised + unnormalised WER but does not publish its")
    add("  normaliser; ours is stated here so numbers are interpretable, not claimed")
    add("  identical to theirs.")
    add("- Numeric accuracy: every expected amount/quantity must be recoverable from")
    add("  the transcript after format normalisation ('5.5k' == 'five k five' == 5500).")
    add("- Transaction accuracy: each raw transcript is fed through the SautiLedger")
    add("  grammar-first normaliser (LLM fallback disabled) and compared to the")
    add("  expected ParseResult.")
    add("- Caveats: small n; tier `sautiledger-clips` is a single speaker (the")
    add("  developer); sw-KE/ha-NG ground truths drafted non-natively pending venue")
    add("  validation. Sahara failures, where they occur, are reported unedited —")
    add("  the claim under test is downstream safety, not raw perfection.")
    add("- Citations: AfriVox / AfriSpeech datasets © Intron Health (CC-BY-4.0 for")
    add("  released subsets); Olatunji et al., *AfriSpeech-200: Pan-African Accented")
    add("  Speech Dataset for Clinical and General Domain ASR* (TACL 2023);")
    add("  github.com/intron-innovation/Intron-Multimodal-Benchmarking.")
    add("")

    out = RESULTS_DIR / "REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    render()
