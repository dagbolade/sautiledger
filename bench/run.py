"""Benchmark runner. One command:  python -m bench.run --confirm  (= make bench)

- Corpus is FROZEN before the first run: the manifest sha256 goes into the
  report; never drop clips after seeing results.
- Raw transcripts are cached to bench/results/raw/<model>/<clip>.json so
  reruns never re-spend API credits.
- Budget guard: prints estimated cloud audio-minutes and refuses to run
  without --confirm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import wave
from pathlib import Path

from sautiledger.config import get_settings  # loads .env for SAHARA_API_KEY
from sautiledger.packs import load_pack

from .metrics import score_clip

BENCH_DIR = Path(__file__).resolve().parent
CORPUS_DIR = BENCH_DIR / "corpus"
RESULTS_DIR = BENCH_DIR / "results"


def load_corpus() -> tuple[list[dict], str]:
    clips: list[dict] = []
    hasher = hashlib.sha256()
    for manifest in sorted(CORPUS_DIR.glob("*/manifest.jsonl")):
        tier = manifest.parent.name
        hasher.update(manifest.read_bytes())
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            clip = json.loads(line)
            clip["tier"] = tier
            clip["audio_path"] = manifest.parent / clip["audio"]
            clips.append(clip)
    return clips, hasher.hexdigest()


def wav_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return 5.0  # non-wav or unreadable: assume a short clip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="actually spend API credits")
    parser.add_argument("--frontier", default="openai", choices=["openai", "gemini", "whisper-small"])
    parser.add_argument("--tier", default=None, help="run one corpus tier only")
    args = parser.parse_args()

    get_settings()  # side effect: loads .env
    clips, manifest_hash = load_corpus()
    if args.tier:
        clips = [c for c in clips if c["tier"] == args.tier]
    present = [c for c in clips if c["audio_path"].exists()]
    missing = [c for c in clips if not c["audio_path"].exists()]
    for clip in missing:
        print(f"  ! missing audio, skipped: {clip['tier']}/{clip['audio']}")
    if not present:
        print("No audio present in bench/corpus/ — record clips or run fetch_afriswitch.py first.")
        sys.exit(1)

    cloud_minutes = sum(wav_seconds(c["audio_path"]) for c in present) / 60
    print(f"Corpus: {len(present)} clips ({len(missing)} missing), manifest sha256 {manifest_hash[:16]}…")
    print(f"Estimated cloud audio per cloud model: {cloud_minutes:.1f} minutes")
    if not args.confirm:
        print("Dry run only. Re-run with --confirm to transcribe.")
        sys.exit(0)

    from .bench_asr import build_models  # heavy imports only after --confirm

    models, notes = build_models(args.frontier)
    results: list[dict] = []
    for model in models:
        raw_dir = RESULTS_DIR / "raw" / model.name
        raw_dir.mkdir(parents=True, exist_ok=True)
        for clip in present:
            cache = raw_dir / f"{clip['id']}.json"
            if cache.exists():
                hyp = json.loads(cache.read_text(encoding="utf-8"))["transcript"]
            else:
                print(f"[{model.name}] {clip['id']} …")
                try:
                    hyp = model.transcribe_file(clip["audio_path"], clip.get("language"))
                except Exception as exc:
                    print(f"  ! {type(exc).__name__}: {exc}")
                    continue
                cache.write_text(
                    json.dumps({"transcript": hyp, "clip": clip["id"]}, ensure_ascii=False),
                    encoding="utf-8",
                )
            pack = load_pack(clip.get("language", "pcm-yo-NG"))
            results.append({
                "model": model.name,
                "clip": clip["id"],
                "tier": clip["tier"],
                "truth": clip["text"],
                "hyp": hyp,
                **score_clip(clip["text"], hyp, clip.get("expected_parse") or {}, pack),
            })

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "manifest_sha256": manifest_hash,
        "notes": notes,
        "n_clips": len(present),
        "n_missing": len(missing),
        "results": results,
    }
    (RESULTS_DIR / "metrics.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {RESULTS_DIR / 'metrics.json'} ({len(results)} rows)")

    from .report import render

    render()


if __name__ == "__main__":
    main()
