"""Supplementary tiers, scored exactly like the frozen benchmark but kept apart.

python -m bench.supplementary --confirm --models sahara-v2.5   # transcribe (cached)
python -m bench.supplementary --score-only                     # score all cached

Tiers live in bench/corpus-supplementary/<tier>/manifest.jsonl. They are NOT
under bench/corpus/, so the frozen corpus hash published in the report
(sha256 over bench/corpus/*/manifest.jsonl) is unaffected. Each supplementary
run records its own manifest hash. Transcripts are cached per model per clip
in bench/results/raw-supplementary/, so scoring can be repeated for free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .run import BENCH_DIR, RESULTS_DIR, _resolve_audio, _score

SUPP_DIR = BENCH_DIR / "corpus-supplementary"
RAW_DIR = RESULTS_DIR / "raw-supplementary"
OUT = RESULTS_DIR / "metrics_supplementary.json"


def load_supplementary() -> tuple[list[dict], str]:
    clips: list[dict] = []
    hasher = hashlib.sha256()
    for manifest in sorted(SUPP_DIR.glob("*/manifest.jsonl")):
        hasher.update(manifest.read_bytes())
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                clip = json.loads(line)
                clip["tier"] = manifest.parent.name
                clip["audio_path"] = _resolve_audio(manifest.parent, clip)
                clips.append(clip)
    return clips, hasher.hexdigest()


def transcribe(clips: list[dict], only: list[str] | None) -> None:
    from .bench_asr import build_models

    models, _notes = build_models("gemini", only=only)
    for model in models:
        out = RAW_DIR / model.name
        out.mkdir(parents=True, exist_ok=True)
        failures = 0
        for clip in clips:
            cache = out / f"{clip['id']}.json"
            if cache.exists() or clip["audio_path"] is None:
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
        print(f"[{model.name}] cached", flush=True)


def score(clips: list[dict], manifest_hash: str) -> list[dict]:
    by_id = {c["id"]: c for c in clips}
    results = []
    for model_dir in sorted(p for p in RAW_DIR.iterdir() if p.is_dir()) if RAW_DIR.exists() else []:
        for cache in sorted(model_dir.glob("*.json")):
            clip = by_id.get(cache.stem)
            if clip is None:
                continue
            hyp = json.loads(cache.read_text(encoding="utf-8"))["transcript"]
            results.append(_score(model_dir.name, clip, hyp))
    OUT.write_text(json.dumps({"manifest_sha256": manifest_hash, "n_clips": len(clips),
                               "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {OUT} ({len(results)} rows), supplementary manifest sha256 {manifest_hash}")
    return results


def summary(results: list[dict], clips: list[dict]) -> None:
    """Per tier and model. Transaction scores are shown twice: over every
    labelled clip, and over label-verified clips only (excluding clips whose
    manifest marks the label uncertain because the audio departs from it)."""
    from collections import defaultdict
    uncertain = {c["id"] for c in clips if c.get("label_uncertain")}
    g = defaultdict(list)
    for r in results:
        g[(r["tier"], r["model"])].append(r)
    mean = lambda v: sum(v) / len(v) if v else 0.0
    for (tier, model), rows in sorted(g.items()):
        lab = [r for r in rows if r["has_expected"]]
        ver = [r for r in lab if r["clip"] not in uncertain]
        print(f"{tier:8} {model:22} n={len(rows):2} WER {mean([r['wer'] for r in rows]):.3f} "
              f"CER {mean([r.get('cer', 0) for r in rows]):.3f} | all {len(lab)}: exact "
              f"{mean([r['exact_match'] for r in lab]):.0%} corrupted {mean([r['amount_corrupted'] for r in lab]):.0%} "
              f"| verified {len(ver)}: exact {mean([r['exact_match'] for r in ver]):.0%} "
              f"corrupted {mean([r['amount_corrupted'] for r in ver]):.0%}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="actually call the models")
    ap.add_argument("--models", default=None)
    ap.add_argument("--score-only", action="store_true")
    args = ap.parse_args()
    from sautiledger.config import get_settings
    get_settings()  # loads .env: API keys for the cloud models
    clips, h = load_supplementary()
    missing = [c["id"] for c in clips if c["audio_path"] is None]
    print(f"{len(clips)} supplementary clips, {len(missing)} missing audio {missing or ''}")
    if args.confirm and not args.score_only:
        transcribe(clips, args.models.split(",") if args.models else None)
    summary(score(clips, h), clips)


if __name__ == "__main__":
    main()
