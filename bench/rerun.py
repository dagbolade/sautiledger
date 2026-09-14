"""Re-run the cloud systems on the frozen corpus and compare with the stored run.

python -m bench.rerun --confirm                 # transcribe into a dated cache
python -m bench.rerun --compare                 # compare dated cache with the frozen run

Hosted models change without notice, so a benchmark is a snapshot. This
re-sends the same frozen audio to the cloud systems and reports, per system
and tier, how many transcripts changed and how the scores moved. New
transcripts go to bench/results/raw-rerun-<date>/; the frozen cache in
bench/results/raw/ and metrics.json are never written. Local models
(Whisper, omnilingual) have fixed weights and are not re-run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

from .run import RESULTS_DIR, _score, load_corpus

CLOUD = ["sahara-v2.5", "mai-transcribe-2", "gpt-4o-transcribe", "chirp-3", "parakeet-tdt"]


def rerun_dir(date: str) -> Path:
    return RESULTS_DIR / f"raw-rerun-{date}"


def transcribe(date: str, models: list[str]) -> None:
    from .bench_asr import build_models

    clips, _ = load_corpus()
    present = [c for c in clips if c["audio_path"] is not None]
    built, _notes = build_models("gemini", only=models)
    for model in built:
        out = rerun_dir(date) / model.name
        out.mkdir(parents=True, exist_ok=True)
        failures = 0
        for clip in present:
            cache = out / f"{clip['id']}.json"
            if cache.exists():
                continue
            try:
                hyp = model.transcribe_file(clip["audio_path"], clip.get("language"))
                failures = 0
            except Exception as exc:
                failures += 1
                print(f"[{model.name}] {clip['id']} ! {type(exc).__name__}: {exc}", flush=True)
                if failures >= 3:
                    print(f"[{model.name}] stopped after 3 consecutive failures", flush=True)
                    break
                continue
            cache.write_text(json.dumps({"transcript": hyp, "clip": clip["id"]}, ensure_ascii=False),
                             encoding="utf-8")
        print(f"[{model.name}] {len(list(out.glob('*.json')))}/{len(present)} cached", flush=True)


def compare(date: str) -> dict:
    clips, manifest_hash = load_corpus()
    by_id = {c["id"]: c for c in clips}
    mean = lambda v: sum(v) / len(v) if v else 0.0
    report = {"date": date, "frozen_manifest_sha256": manifest_hash, "systems": []}
    for model in CLOUD:
        new_dir = rerun_dir(date) / model
        old_dir = RESULTS_DIR / "raw" / model
        if not new_dir.exists():
            continue
        per_tier = defaultdict(lambda: {"old": [], "new": [], "changed": 0, "n": 0})
        examples = []
        for cache in sorted(new_dir.glob("*.json")):
            clip = by_id.get(cache.stem)
            old_file = old_dir / cache.name
            if clip is None or not old_file.exists():
                continue
            old_hyp = json.loads(old_file.read_text(encoding="utf-8"))["transcript"]
            new_hyp = json.loads(cache.read_text(encoding="utf-8"))["transcript"]
            t = per_tier[clip["tier"]]
            t["n"] += 1
            t["old"].append(_score(model, clip, old_hyp))
            t["new"].append(_score(model, clip, new_hyp))
            if old_hyp.strip() != new_hyp.strip():
                t["changed"] += 1
                if clip["tier"] != "afriswitch-sample" and len(examples) < 3:
                    examples.append({"clip": clip["id"], "before": old_hyp, "after": new_hyp})
        tiers = {}
        for tier, t in sorted(per_tier.items()):
            lab_o = [r for r in t["old"] if r["has_expected"]]
            lab_n = [r for r in t["new"] if r["has_expected"]]
            tiers[tier] = {
                "clips": t["n"], "transcripts_changed": t["changed"],
                "wer": [round(mean([r["wer"] for r in t["old"]]), 3), round(mean([r["wer"] for r in t["new"]]), 3)],
                "cer": [round(mean([r.get("cer", 0) for r in t["old"]]), 3), round(mean([r.get("cer", 0) for r in t["new"]]), 3)],
                "exact": [round(mean([r["exact_match"] for r in lab_o]), 3), round(mean([r["exact_match"] for r in lab_n]), 3)] if lab_o else None,
                "corrupted": [round(mean([r["amount_corrupted"] for r in lab_o]), 3), round(mean([r["amount_corrupted"] for r in lab_n]), 3)] if lab_o else None,
            }
        report["systems"].append({"model": model, "tiers": tiers, "examples": examples})
    out = RESULTS_DIR / f"rerun-{date}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in report["systems"]:
        for tier, v in s["tiers"].items():
            ex = f" exact {v['exact'][0]:.0%}->{v['exact'][1]:.0%} corrupted {v['corrupted'][0]:.0%}->{v['corrupted'][1]:.0%}" if v["exact"] else ""
            print(f"{s['model']:18} {tier:18} changed {v['transcripts_changed']:2}/{v['clips']:2}  "
                  f"WER {v['wer'][0]:.3f}->{v['wer'][1]:.3f}  CER {v['cer'][0]:.3f}->{v['cer'][1]:.3f}{ex}")
    print(f"Wrote {out}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--models", default=",".join(CLOUD))
    args = ap.parse_args()
    from sautiledger.config import get_settings
    get_settings()
    if args.confirm:
        transcribe(args.date, args.models.split(","))
    if args.compare or args.confirm:
        compare(args.date)


if __name__ == "__main__":
    main()
