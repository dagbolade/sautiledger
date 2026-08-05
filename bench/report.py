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


def _amendments_section(add) -> None:
    """v1 vs v2 before/after, computed from metrics_v1.json (frozen v1
    scoring) against the current metrics.json (v2 grammar)."""
    v1_path = RESULTS_DIR / "metrics_v1.json"
    if not v1_path.exists():
        return
    v1 = json.loads(v1_path.read_text(encoding="utf-8"))["results"]
    # v1 vs v2 isolates the grammar amendments (both scored on the same audio);
    # the audio-correction section below covers v2 vs v3.
    v2_path = RESULTS_DIR / "metrics_v2.json"
    v2_source = v2_path if v2_path.exists() else (RESULTS_DIR / "metrics.json")
    v2 = json.loads(v2_source.read_text(encoding="utf-8"))["results"]

    add("## Amendments (v2 grammar) — documented post-freeze changes")
    add("")
    add("Two grammar amendments were applied AFTER the v1 scoring, motivated by")
    add("observed ASR behaviour. The corpus, transcripts, and v1 numbers are frozen")
    add("(`metrics_v1.json`); v2 re-scores the SAME cached transcripts — no new audio,")
    add("no new API calls. Both scorings are reported.")
    add("")
    add("1. **Digit-twin rule** (pcm-yo-NG): `[N]k [M]` → N×1000 + M×100, so \"5k 5\"")
    add("   parses as 5,500. Sahara demonstrably emits the digit twin of the native-")
    add("   validated spoken \"N thousand M\" form; refusing it was the grammar not")
    add("   speaking Sahara's output dialect, not safety.")
    add("2. **Flattened-distributive guard**: any parse with quantity ≥ 2 and a single")
    add("   bare numeral amount downgrades to a clarify (\"₦X for each one, or ₦X for")
    add("   everything?\"). ASR numeric normalisation can collapse reduplication")
    add("   (\"two two fifty\" → \"250\") before the grammar sees it — in v1 this logged")
    add("   half the true bill. Includes quantity recovery: a leading numeral in item")
    add("   position counts as quantity when the unit word was mangled (\"2 pint of…\").")
    add("")
    add("Before/after on the parse-ground-truth tier (`sautiledger-clips`):")
    add("")
    add("| Model | Txn exact v1→v2 | Amount safe v1→v2 | **Amount corrupted v1→v2** | Numeric acc v1→v2 |")
    add("|---|---|---|---|---|")

    def agg(rows, model):
        sel = [r for r in rows if r["model"] == model and r["tier"] == "sautiledger-clips"
               and r.get("has_expected", True)]
        return {
            "exact": _pct([r["exact_match"] for r in sel]),
            "safe": _pct([r["amount_safe"] for r in sel]),
            "corr": _pct([r["amount_corrupted"] for r in sel]),
            "num": _pct([r["numeric_accuracy"] for r in sel]),
        }

    models = sorted({r["model"] for r in v2 if r["tier"] == "sautiledger-clips"})
    for model in models:
        a, b = agg(v1, model), agg(v2, model)
        add(f"| {model} | {a['exact']} → {b['exact']} | {a['safe']} → {b['safe']} "
            f"| **{a['corr']} → {b['corr']}** | {a['num']} → {b['num']} |")
    add("")
    add("Every movement is shown above, favourable or not — v1 remains the scoring of")
    add("record for the frozen grammar; v2 is the scoring of the shipped product.")
    add("")
    add("**The guard did not reach 0% for sahara-v2** (expected 0%, actual above). The")
    add("two residual corruptions are a DIFFERENT failure class — word deletion, not")
    add("flattening: (1) \"ten thousand naira\" → \"Abil thousand naira\", the deleted")
    add("multiplier leaving a bare \"thousand\" that logs ₦1,000 for a ₦10,000 expense;")
    add("(2) the doubled correction trigger \"no no na…\" transcribed with a single")
    add("\"no\", turning an amount correction into a spurious ₦500 sale. No")
    add("deterministic guard catches deletions without over-asking on legitimate")
    add("speech (\"one thousand\" is a real amount). These stand as the honest floor of")
    add("the current design and the first item on the post-hackathon roadmap")
    add("(confidence-weighted readback: low-confidence numerals echo the FULL amount")
    add("back before commit).")
    add("")


def _audio_correction_section(add) -> None:
    """v2 vs v3: tier-a re-measured after the audio-conversion fix."""
    v2_path = RESULTS_DIR / "metrics_v2.json"
    if not v2_path.exists():
        return
    v2 = json.loads(v2_path.read_text(encoding="utf-8"))["results"]
    v3 = json.loads((RESULTS_DIR / "metrics.json").read_text(encoding="utf-8"))["results"]

    add("## Audio-conversion correction (v3) — tier-a re-measured")
    add("")
    add("After the v2 scoring, an A/B test against the vendor's own web UI showed")
    add("materially better transcripts for the same clip. Root cause was NOT the")
    add("language configuration (verified correct and API-validated): the corpus")
    add("conversion step was time-stretching every tier-a clip by ~1.26x — a")
    add("resampler bug copying frame padding as samples. ALL tier-a v1/v2 numbers")
    add("for ALL models were measured on that corrupted audio. The corpus was")
    add("re-converted from the preserved originals (15/15 duration-matched) and")
    add("tier-a re-measured for every model as v3. Tier-b audio was never")
    add("re-encoded and is unaffected; its results are unchanged.")
    add("")
    add("| Model | WER v2→v3 | Numeric acc v2→v3 | Txn exact v2→v3 | Amount safe v2→v3 | **Amount corrupted v2→v3** |")
    add("|---|---|---|---|---|---|")

    def agg(rows, model):
        sel = [r for r in rows if r["model"] == model and r["tier"] == "sautiledger-clips"
               and r.get("has_expected", True)]
        return {
            "wer": _pct([r["wer"] for r in sel]),
            "num": _pct([r["numeric_accuracy"] for r in sel]),
            "exact": _pct([r["exact_match"] for r in sel]),
            "safe": _pct([r["amount_safe"] for r in sel]),
            "corr": _pct([r["amount_corrupted"] for r in sel]),
        }

    models = sorted({r["model"] for r in v3 if r["tier"] == "sautiledger-clips"})
    for model in models:
        a, b = agg(v2, model), agg(v3, model)
        add(f"| {model} | {a['wer']} → {b['wer']} | {a['num']} → {b['num']} "
            f"| {a['exact']} → {b['exact']} | {a['safe']} → {b['safe']} "
            f"| **{a['corr']} → {b['corr']}** |")
    add("")
    add("Both scorings are preserved (`metrics_v2.json`, `metrics.json`); the")
    add("product ships with the corrected audio path regardless of these numbers.")
    add("")


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
            with_gt = [r for r in group if r.get("has_expected", True)]
            add(
                f"| {model} | {_pct([r['wer'] for r in group])} | {_pct([r['wer_raw'] for r in group])} "
                f"| {_pct([r['numeric_accuracy'] for r in with_gt])} | {_pct([r['exact_match'] for r in with_gt])} "
                f"| {_pct([r['amount_safe'] for r in with_gt])} | **{_pct([r['amount_corrupted'] for r in with_gt])}** |"
            )
        if not any(r.get("has_expected", True) for _, g in by_tier_model.items() for r in g if r["tier"] == tier):
            add("")
            add("*(no parse ground truth in this tier: WER columns only)*")
        add("")

    add("The three-level transaction metric is the point: WER alone understates the")
    add("differences for financial use. *Amount corrupted* counts transcripts that made")
    add("our normaliser log a WRONG amount — the failure a market trader cannot afford.")
    add("*Amount safe* includes clarify outcomes: an agent that asks is safe, an agent")
    add("that guesses is not. Transcription accuracy is necessary but not sufficient for")
    add("financial records; the grammar-first normaliser + clarify design is the safety")
    add("layer, and the amount-corrupted column is the evidence of what it repairs.")
    add("")

    add("### A caveat on WER for financial speech")
    add("")
    add("Sahara's tier-a WER is inflated by digit renderings that are semantically")
    add("correct: it transcribes spoken \"five thousand five\" as \"5k 5\" — every such")
    add("token counts as a word error against the spoken-form ground truth even though")
    add("the number is right. This is itself evidence that WER is the wrong lens for")
    add("financial speech, and why the numeric and transaction metrics exist.")
    add("")

    add("## Findings")
    add("")
    add("**(a) Only one model produced a usable ledger.** On the transaction metric,")
    add("sahara-v2 achieved several times the exact-transaction rate of either whisper")
    add("model — the whisper transcripts of Pidgin market speech were mostly not")
    add("parseable as transactions at all. For this application there is one viable")
    add("ASR, and it is the one trained on this speech.")
    add("")
    add("**(b) The corruption inversion.** whisper-small posts the LOWEST amount-")
    add("corrupted rate — not because it is safe, but because its output is noise the")
    add("grammar refuses to parse, which the agent converts into clarify questions.")
    add("sahara-v2, being far more plausible, is the only model whose errors survive")
    add("parsing — a plausible-but-flattened transcript is more dangerous than a")
    add("garbled one. Downstream safety must be engineered, not assumed from accuracy:")
    add("that is what the v2 flattened-distributive guard does.")
    add("")
    add("**(c) The predicted meaning inversion appeared in the wild.** Both whisper")
    add("models transcribed perfective \"I don sell\" as negated \"I don't sell\" on the")
    add("same clip — flagged automatically by the harness (see examples). An agent")
    add("acting on the negation would drop a real sale from the record.")
    add("")

    _amendments_section(add)
    _audio_correction_section(add)

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

    add("### The reduplication finding")
    add("")
    add("Case 4 (\"two two fifty\") was originally specced as an ambiguity requiring")
    add("a clarify question. Native-speaker review corrected this: in Nigerian Pidgin,")
    add("reduplicated money **is** the distributive — 250 each, unambiguously. An")
    add("outsider (and the AI that drafted the corpus) hears ambiguity where native")
    add("grammar encodes meaning. The parse rule now lives in the pcm-yo-NG pack,")
    add("gated off for packs that have not had native validation.")
    add("")
    add("## Methodology & caveats")
    add("")
    add("- Provenance: tier-a utterances were drafted by an AI assistant and CORRECTED")
    add("  by a native Nigerian Pidgin/Yoruba speaker before recording; sw-KE and ha-NG")
    add("  cases remain non-native drafts pending venue validation (flagged per-case).")
    add("  Even the test corpus required native-speaker repair — the same gap the")
    add("  product exists to close.")
    add("- Licence: AfriSwitch (CC BY-NC-SA 4.0) is used for evaluation only, never")
    add("  redistributed, and not used to train or build the product.")
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
    add("- Citations: **AfriSwitch** (huggingface.co/datasets/intronhealth/AfriSwitch,")
    add("  licence CC BY-NC-SA 4.0; 54.41h / 16,602 code-switched utterances across")
    add("  14 African languages paired with English; used here for non-commercial")
    add("  benchmarking, samples fetched at run time and never redistributed);")
    add("  AfriVox / AfriSpeech datasets © Intron Health; Olatunji et al.,")
    add("  *AfriSpeech-200: Pan-African Accented Speech Dataset for Clinical and")
    add("  General Domain ASR* (TACL 2023);")
    add("  github.com/intron-innovation/Intron-Multimodal-Benchmarking.")
    add("")

    out = RESULTS_DIR / "REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    render()
