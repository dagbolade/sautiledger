"""Renders the Phase 2 (Main Challenge) benchmark report from metrics.json.

Distinct from report.py, which renders the frozen August workshop report
(preserved as REPORT-workshop-2026-08.md and cited here as prior work).

Structure follows the organisers' stated priorities:
  (a) the DOWNSTREAM TASK-COMPLETION metric leads — Tobi Olatunji, Intron,
      at the 28 Aug masterclass: teams should measure "how many
      transactions were actually correctly recorded";
  (b) standard WER/CER (normalised AND raw) follows, matching Intron's own
      Intron-Multimodal-Benchmarking practice and Microsoft's PazaBench;
  (c) a per-group disparity section, motivated by ASR-FairBench
      (Rai et al., Interspeech 2025), which the organisers recommended.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"

PROS_CONS = {
    "sahara-v2.5": (
        "**Pros:** built for exactly this speech — code-switched African utterances, "
        "dense numbers, market vocabulary; the only model that renders Nigerian "
        "Pidgin grammar as Pidgin rather than anglicising it. Ships TTS in the same "
        "voice register, so the readback matches the input language. "
        "**Cons:** cloud-only (offline deployment is enterprise-tier), no model/version "
        "field in responses, and its LLM post-corrections are on by default — helpful "
        "for readability, but they reformat digits in ways a downstream parser must "
        "be written to expect."
    ),
    "sahara-v2.5-raw": (
        "The same acoustic model with `use_disable_llm_corrections=TRUE`. **Pros:** "
        "shows what the recogniser actually heard, before an LLM tidies it. "
        "**Cons:** not the default any integrator gets, so it is the scientific "
        "control, not the shipping configuration."
    ),
    "whisper-large-v3": (
        "**Pros:** strong general-purpose local model, fully offline, no per-call cost. "
        "**Cons:** anglicises code-switched speech — the error class that corrupts "
        "amounts downstream — and inverts Pidgin's perfective 'I don sell' into the "
        "negated 'I don't sell', which reverses the meaning of a sale."
    ),
    "whisper-small": (
        "**Pros:** fast, offline, tiny. **Cons:** weakest on accented code-switched "
        "speech; used here as the frontier substitute because no frontier API key was "
        "available. Treat its numbers as a floor, not a fair frontier baseline."
    ),
    "omnilingual-ctc-300m": (
        "Meta's omnilingual-ASR (CTC, 300M), open weights (Apache-2.0), run locally "
        "via fairseq2. **Pros:** the strongest open model on our languages in "
        "Microsoft's PazaBench, claims 1,672 languages including `pcm_Latn` and "
        "`sna_Latn`, costs nothing to run, and is the only model in this benchmark "
        "that renders Yoruba numerals with correct diacritics. **Cons:** no Windows "
        "build (needs WSL/Linux), ~20s per clip on CPU, and it transcribes "
        "phonetically rather than semantically — it hears the words but drops or "
        "mangles the digits that a ledger depends on."
    ),
    "gemini-3-flash": (
        "Frontier multimodal model with audio input. **Cons:** cloud-only, and "
        "transcript phrasing drifts toward standard English, breaking Pidgin grammar "
        "cues."
    ),
    "gpt-4o-transcribe": (
        "Frontier multimodal ASR; strong on clean accented English, unknown exposure "
        "to Pidgin/Yoruba market speech. Cloud-only and per-call priced."
    ),
}

TIER_LABEL = {
    "sautiledger-clips": "tier-a — native-recorded market utterances (Nigerian "
                         "Pidgin/Yoruba/English), parse ground truth",
    "sh-clips": "tier-sh — native-recorded Shona/English market utterances, parse "
                "ground truth (NEW for Phase 2)",
    "afriswitch-sample": "tier-b — AfriSwitch code-switched broadcast speech, "
                         "transcript ground truth only",
}


def _pct(values) -> str:
    if not values:
        return "–"
    if isinstance(values[0], bool):
        return f"{100 * sum(values) / len(values):.0f}%"
    return f"{100 * sum(values) / len(values):.1f}%"


def _mean(values) -> float:
    return sum(values) / len(values) if values else 0.0


def render() -> Path:
    data = json.loads((RESULTS_DIR / "metrics.json").read_text(encoding="utf-8"))
    rows = data["results"]
    models = sorted({r["model"] for r in rows})
    tiers = sorted({r["tier"] for r in rows})

    def sel(model=None, tier=None, gt_only=False):
        out = rows
        if model:
            out = [r for r in out if r["model"] == model]
        if tier:
            out = [r for r in out if r["tier"] == tier]
        if gt_only:
            out = [r for r in out if r.get("has_expected", True)]
        return out

    lines: list[str] = []
    add = lines.append

    add("# SautiLedger — Code-Switch ASR & TTS Benchmark")
    add("")
    add("**Sahara CodeSwitch Africa Challenge (Phase 2) — benchmark report**")
    add("")
    add(f"Corpus frozen before the first run; manifest sha256 `{data['manifest_sha256']}`. ")
    add(f"Clips scored: {data['n_clips']}. Models: {len(models)}.")
    add("")
    for note in data.get("notes", []):
        add(f"> **Note:** {note}")
    add("")
    add("Prior work: this benchmark extends our August workshop report "
        "(`REPORT-workshop-2026-08.md`, same repository), which measured three "
        "models on the tier-a and tier-b corpora. Everything below is a fresh "
        "measurement; where the workshop numbers are cited they are labelled as "
        "the 5 August snapshot.")
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. The primary result: task completion")
    add("")
    add("At Intron's 28 August masterclass the challenge founder was explicit about "
        "the metric teams should develop for their own vertical — for a financial "
        "application, *\"how many transactions were actually correctly recorded\"*. "
        "That is the metric this section reports, and we lead with it because a "
        "voice ledger is judged by the ledger, not by the transcript.")
    add("")
    add("Each model's **raw transcript** is fed through SautiLedger's grammar-first "
        "normaliser exactly as the live app runs it (LLM fallback disabled), and the "
        "resulting entry is compared to the expected one:")
    add("")
    add("- **Transaction exact** — every field correct: type, item, quantity, unit, amount.")
    add("- **Amount safe** — the amount was right, *or* the agent refused to guess and "
        "asked a clarifying question. Asking is safe; nothing is written.")
    add("- **Amount corrupted** — a WRONG amount would have been written into "
        "someone's money records. This is the number that matters.")
    add("")
    gt_tiers = [t for t in tiers if any(r.get("has_expected") for r in sel(tier=t))]
    for tier in gt_tiers:
        add(f"### {TIER_LABEL.get(tier, tier)}")
        add("")
        add("| Model | Transaction exact | Amount safe | **Amount corrupted** | Numeric accuracy |")
        add("|---|---|---|---|---|")
        for model in models:
            g = sel(model=model, tier=tier, gt_only=True)
            if not g:
                continue
            add(f"| `{model}` | {_pct([r['exact_match'] for r in g])} "
                f"| {_pct([r['amount_safe'] for r in g])} "
                f"| **{_pct([r['amount_corrupted'] for r in g])}** "
                f"| {_pct([r['numeric_accuracy'] for r in g])} |")
        add("")

    # ---------------------------------------------------------------- 2
    add("## 2. Standard transcription metrics (WER / CER)")
    add("")
    add("Reported for comparability with general-purpose leaderboards. Both "
        "normalised and raw are given, matching Intron's own "
        "`Intron-Multimodal-Benchmarking` practice; CER is included because "
        "Microsoft's PazaBench leads with it, and because it is the fairer metric "
        "for morphologically rich languages where one wrong affix costs an entire "
        "word under WER. Normalisation = lowercase, punctuation stripped, "
        "whitespace collapsed, diacritics folded (jiwer-standard conventions; "
        "Intron does not publish its own normaliser, so ours is stated rather than "
        "claimed identical).")
    add("")
    for tier in tiers:
        add(f"### {TIER_LABEL.get(tier, tier)}")
        add("")
        add("| Model | WER (norm) | WER (raw) | CER (norm) | CER (raw) |")
        add("|---|---|---|---|---|")
        for model in models:
            g = sel(model=model, tier=tier)
            if not g:
                continue
            add(f"| `{model}` | {_mean([r['wer'] for r in g]):.3f} "
                f"| {_mean([r['wer_raw'] for r in g]):.3f} "
                f"| {_mean([r.get('cer', 0) for r in g]):.3f} "
                f"| {_mean([r.get('cer_raw', 0) for r in g]):.3f} |")
        add("")
    add("**A caveat on WER for financial speech.** Sahara transcribes spoken "
        "\"five thousand five\" as \"5,500\" — semantically exact, but every such "
        "token counts as a word error against a spoken-form reference. WER "
        "penalises the model for being *more* useful downstream. This is precisely "
        "why the task-completion metric in §1 leads this report.")
    add("")

    # ---------------------------------------------------------------- 3
    add("## 3. Performance disparity across speaker groups")
    add("")
    add("The organisers recommended ASR-FairBench (Rai et al., *Measuring and "
        "Benchmarking Equity Across Speech Recognition Systems*, Interspeech 2025), "
        "which argues that a single aggregate WER hides systematic disparities "
        "between speaker groups, and combines fairness with accuracy into a "
        "Fairness-Adjusted ASR Score. We cannot compute FAAS itself — it requires "
        "the Fair-Speech corpus with per-speaker demographic labels and a "
        "mixed-effects Poisson regression over hundreds of speakers, and our "
        "corpus has four speaker groups — but the underlying point applies "
        "directly, so we report the disparity rather than hiding behind an "
        "average.")
    add("")
    add("Group = corpus tier × language, which here also separates speakers "
        "(tier-a is one Nigerian male speaker; tier-sh is one Zimbabwean female "
        "speaker; tier-b is many broadcast speakers across languages).")
    add("")
    add("| Model | " + " | ".join(f"{t.replace('-clips','').replace('-sample','')} WER"
                                  for t in tiers) + " | **Disparity (worst ÷ best)** |")
    add("|---" * (len(tiers) + 2) + "|")
    for model in models:
        cells, vals = [], []
        for tier in tiers:
            g = sel(model=model, tier=tier)
            if g:
                m = _mean([r["wer"] for r in g])
                cells.append(f"{m:.3f}")
                vals.append(m)
            else:
                cells.append("–")
        ratio = (max(vals) / min(vals)) if vals and min(vals) > 0 else 0
        add(f"| `{model}` | " + " | ".join(cells) + f" | **{ratio:.2f}×** |")
    add("")
    add("A model with a low average but a high disparity ratio is not a model that "
        "works for everyone — it is a model that works for whoever resembles its "
        "training data. For a product whose users are, by definition, the speakers "
        "least represented in mainstream speech corpora, that ratio is a product "
        "risk, not a footnote.")
    add("")

    # ---------------------------------------------------------------- 4
    add("## 4. Ablation: does Sahara's LLM post-correction help or hurt?")
    add("")
    add("Sahara's sync endpoint applies LLM corrections to transcripts **by "
        "default** (`use_disable_llm_corrections` defaults to FALSE — found by "
        "reading the API documentation in full, not stated in any tutorial). Every "
        "integrator therefore benchmarks a recogniser *plus a rewriter* without "
        "necessarily knowing it. We measured both configurations on identical audio.")
    add("")
    pair = [m for m in models if m.startswith("sahara-v2.5")]
    if len(pair) == 2:
        add("| Configuration | WER (norm) | CER (norm) | Transaction exact | **Amount corrupted** |")
        add("|---|---|---|---|---|")
        for model in pair:
            g_all = sel(model=model)
            g_gt = sel(model=model, gt_only=True)
            add(f"| `{model}` | {_mean([r['wer'] for r in g_all]):.3f} "
                f"| {_mean([r.get('cer', 0) for r in g_all]):.3f} "
                f"| {_pct([r['exact_match'] for r in g_gt])} "
                f"| **{_pct([r['amount_corrupted'] for r in g_gt])}** |")
        add("")

    # ---------------------------------------------------------------- 5
    add("## 5. A prediction registered in advance: Shona")
    add("")
    add("Before running this benchmark we recorded a falsifiable prediction "
        "(`bench/PHASE-G-NOTES.md`, committed 3 September, before any Shona audio "
        "existed): Sahara's documentation lists Shona (`sn`) as a supported STT "
        "language **and** a supported TTS voice, but Shona is *not* among its 12 "
        "documented code-switching pairs. Our Shona validator's utterances are "
        "heavily code-mixed by design (\"Ndatengesa three cups dze rice nefive "
        "dollars fifty\"). We therefore predicted degraded performance on tier-sh "
        "relative to tier-a, and said so before we could see the result.")
    add("")
    if "sh-clips" in tiers:
        add("| Model | tier-a WER | tier-sh WER | tier-sh transaction exact | **tier-sh amount corrupted** |")
        add("|---|---|---|---|---|")
        for model in models:
            a = sel(model=model, tier="sautiledger-clips")
            s = sel(model=model, tier="sh-clips")
            sg = sel(model=model, tier="sh-clips", gt_only=True)
            if not s:
                continue
            add(f"| `{model}` | {_mean([r['wer'] for r in a]):.3f} "
                f"| {_mean([r['wer'] for r in s]):.3f} "
                f"| {_pct([r['exact_match'] for r in sg])} "
                f"| **{_pct([r['amount_corrupted'] for r in sg])}** |")
        add("")
    add("The Shona corpus was built the same way the Pidgin/Yoruba one was: a "
        "native speaker rewrote every drafted sentence into what a trader would "
        "actually say, chose the currency register (US dollars, spoken as "
        "\"two fifty\" for $2.50), and recorded all 15 utterances herself. Her "
        "corrections taught the parser three things no outsider would have "
        "guessed: `hwani` marks per-unit pricing, concord prefixes glue onto "
        "code-switched numerals (`nefive`, `yeten`), and a trailing copula "
        "(`... pack is 4000`) marks a price rather than part of the item name.")
    add("")

    # ---------------------------------------------------------------- 6
    add("## 6. Illustrative transcripts")
    add("")
    by_clip: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_clip[row["clip"]].append(row)
    flagged = [kv for kv in by_clip.items() if any(r["flags"] for r in kv[1])]
    corrupt = [kv for kv in by_clip.items()
               if any(r["amount_corrupted"] for r in kv[1]) and kv not in flagged]
    spread = sorted(by_clip.items(),
                    key=lambda kv: -(max(r["wer"] for r in kv[1]) - min(r["wer"] for r in kv[1])))
    picked, seen = [], set()
    for kv in flagged + corrupt + spread:
        if kv[0] in seen:
            continue
        seen.add(kv[0])
        picked.append(kv)
        if len(picked) >= 6:
            break
    for clip_id, group in picked:
        add(f"**{clip_id}** — truth: `{group[0]['truth']}`")
        add("")
        for row in sorted(group, key=lambda r: r["model"]):
            flags = f"  ⚠ {', '.join(row['flags'])}" if row["flags"] else ""
            bad = "  ✗ AMOUNT CORRUPTED" if row["amount_corrupted"] else ""
            add(f"- `{row['model']}`: `{row['hyp']}`{flags}{bad}")
        add("")

    # ---------------------------------------------------------------- 7
    add("## 7. Per-model assessment")
    add("")
    for model in models:
        add(f"**`{model}`** — {PROS_CONS.get(model, 'No notes.')}")
        add("")

    # ---------------------------------------------------------------- 8 TTS
    tts_path = RESULTS_DIR / "tts_metrics.json"
    if tts_path.exists():
        tts = json.loads(tts_path.read_text(encoding="utf-8"))
        add("## 8. Text-to-speech benchmark (round-trip)")
        add("")
        add("SautiLedger speaks every confirmation aloud, so the TTS is part of the "
            "safety loop, not decoration: a trader who cannot hear the amount "
            "cannot catch our mistake. Intron asked TTS entrants to report "
            "hallucination, transcript loss, segment loss, WER and accuracy. The "
            "paper they cite (ASR-FairBench) is an ASR fairness benchmark and does "
            "not define these, so we define them explicitly and measure them by "
            "**round trip**: the app's real confirmation lines are synthesised, "
            f"then transcribed back by a NEUTRAL third-party ASR (`{tts['judge']}`, "
            "never Sahara's own recogniser, which would be same-vendor circular), "
            "and the transcript is compared to the input text.")
        add("")
        add("| Metric | Definition |")
        add("|---|---|")
        add("| WER | (S+D+I)/N over the round trip |")
        add("| Accuracy | utterance-level exact match after normalisation |")
        add("| Transcript loss | D/N — input words that vanished in the audio |")
        add("| Hallucination | I/N — words that appeared from nowhere |")
        add("| Segment loss | longest contiguous deletion ÷ N — a dropped *phrase*, which D/N alone hides |")
        add("| **Amount survival** | did the money figure survive the round trip? |")
        add("")
        systems = sorted({r["system"] for r in tts["results"]})
        add("| System | WER | Accuracy | Transcript loss | Hallucination | Segment loss | **Amount survival** |")
        add("|---|---|---|---|---|---|---|")
        for system in systems:
            g = [r for r in tts["results"] if r["system"] == system]
            amt = [r for r in g if r["amount_survived"] is not None]
            add(f"| `{system}` | {_mean([r['wer'] for r in g]):.3f} "
                f"| {_mean([r['accuracy'] for r in g]):.2f} "
                f"| {_mean([r['transcript_loss'] for r in g]):.3f} "
                f"| {_mean([r['hallucination'] for r in g]):.3f} "
                f"| {_mean([r['segment_loss'] for r in g]):.3f} "
                f"| **{_pct([bool(r['amount_survived']) for r in amt])}** |")
        add("")
        for note in tts.get("notes", []):
            add(f"> **Note:** {note}")
        add("")

    # ---------------------------------------------------------------- 9
    add("## 9. Product feedback to Intron")
    add("")
    add("Offered in the spirit the challenge asked for — everything below was "
        "observed while building on the API, with traces retained.")
    add("")
    add("1. **Streaming STT never returns `COMMITTED_TRANSCRIPT`.** Sending "
        "`COMMIT` is answered with `INPUT_ERROR: \"Error processing data\"`, "
        "verified repeatedly (26 Aug, and again on v2.5 on 2 September with "
        "real-time-paced chunks). Our client works around it by treating the last "
        "`PARTIAL_TRANSCRIPT` as final. First partial arrives ~10s after commit, "
        "so streaming is currently slower than the sync endpoint for short "
        "utterances; we ship with streaming disabled and a one-variable switch to "
        "re-enable it.")
    add("2. **Unknown form fields are silently ignored.** Posting `language=pcm` "
        "instead of `use_language_asr_input=pcm` does not error — the request "
        "quietly falls back to English ASR and returns a confident, wrong-language "
        "transcript. This cost us a day of chasing a phantom model regression. "
        "Rejecting unknown `use_*` fields, or echoing the effective configuration "
        "in the response, would prevent an entire class of silent integration bugs.")
    add("3. **No model or version identifier in any response.** We measured "
        "deterministic changes in output on identical audio between 5 August and "
        "2 September. Benchmarks are not reproducible against a moving, unlabelled "
        "backend; a `model_version` field would fix this.")
    add("4. **Shona is a supported language but not a supported code-switch pair.** "
        "AfriSwitch itself ships 3.86 h of Shona at CMI 24.55 — among the most "
        "balanced code-mixing in the dataset — so the data to close this gap "
        "already exists in-house.")
    add("5. **TTS accent values are language-named and undocumented in tutorials.** "
        "Finding `voice_language=\"pcm\"` + `voice_accent=\"pidgin\"` required "
        "probing; the combination is correct and produces a genuinely Nigerian "
        "voice, which materially improved how our testers received the app.")
    add("")

    # ---------------------------------------------------------------- 10
    add("## 10. Related work and how this benchmark differs")
    add("")
    add("- **PazaBench** (Microsoft Research Africa; `aka.ms/pazabench`) — the ASR "
        "leaderboard for low-resource languages, 61 African languages × 53 models. "
        "Snapshot taken 28 August (`results/pazabench-wer-2026-08-28.md`). Two "
        "verified gaps motivate this work: **Nigerian Pidgin does not appear among "
        "its 61 languages**, and **no Intron/Sahara model appears among its 53 "
        "models**. Note the precision: omnilingual-ASR *claims* `pcm_Latn` support, "
        "so the gap is in public *evaluation*, not claimed coverage — and to our "
        "knowledge this report contains the first published Pidgin numbers for it.")
    add("- **ASR-FairBench** (Rai et al., Interspeech 2025) — motivates §3. Their "
        "core argument, that aggregate accuracy conceals group disparity, is the "
        "reason we report per-group WER and a disparity ratio.")
    add("- **AfriSwitch** (`intronhealth/AfriSwitch`, CC BY-NC-SA 4.0) — 54.41 h / "
        "16,602 code-switched utterances across 14 African languages. Re-checked "
        "on 7 September, the eve of our corpus freeze: still 14 languages, "
        "unchanged since 3 August. Used for evaluation only, never redistributed, "
        "never used to train the product.")
    add("- **LyngualLabs Yoruba-English code-switching** — listed in Intron's "
        "code-switching collection and worth an honourable mention, but it is a "
        "**TTS model** (a VoxCPM2 fine-tune), not a corpus: it has no human audio "
        "paired with ground-truth transcripts, and benchmarking ASR on synthesised "
        "speech would be circular. It is therefore cited, not used.")
    add("")
    add("**Mercy Muchai** (Microsoft Research Africa), at the same masterclass, "
        "made the point this corpus is built around: code-switching evaluation "
        "requires datasets that are themselves code-mixed — a single-language "
        "corpus cannot measure it. Our tier-a and tier-sh corpora are natively "
        "recorded code-mixed market speech, and tier-b is AfriSwitch.")
    add("")

    # ---------------------------------------------------------------- 11
    add("## 11. Methodology, provenance and caveats")
    add("")
    add("- **Corpus frozen before the first run.** The manifest sha256 is printed "
        "at the top of this report; no clip was added or dropped after seeing any "
        "result. Raw transcripts are cached per clip per model, so every number "
        "here is reproducible without re-spending API credits.")
    add("- **Provenance.** tier-a utterances were drafted by an AI assistant and "
        "then CORRECTED by a native Nigerian Pidgin/Yoruba speaker before "
        "recording; tier-sh identically, by a native Shona speaker (7 September). "
        "The sw-KE and ha-NG cases remain non-native drafts and are flagged as "
        "such — they are excluded from the recorded tiers rather than presented as "
        "validated. Even our test corpus needed native repair: that is the same "
        "gap the product exists to close.")
    add("- **Transaction accuracy** feeds each raw transcript through the shipped "
        "grammar-first normaliser with the LLM fallback disabled, so the number "
        "reflects deterministic behaviour only.")
    add("- **Diacritic folding.** omnilingual returns correctly accented Yoruba "
        "(`ẹgbẹrùn mẹ́ta`). Our scorer folds diacritics before comparison, because "
        "penalising a model for orthographic faithfulness the reference lacks "
        "would be a bias in *our* instrument. The fold is a no-op on ASCII output, "
        "so it does not advantage any model.")
    add("- **Caveats.** Small n per tier; tier-a is a single speaker and tier-sh is "
        "a single speaker, so their WERs describe those voices, not their "
        "languages. No frontier API model was available (no key); whisper-small "
        "substitutes and is labelled as a floor. Sahara failures are reported "
        "unedited — the claim under test is downstream safety, not vendor "
        "perfection.")
    add("")

    out = RESULTS_DIR / "REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({len(lines)} lines)")
    return out


if __name__ == "__main__":
    render()
