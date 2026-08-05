"""Benchmark runner.

  python -m bench.run                  # dry: corpus + spend estimate only
  python -m bench.run --fake           # = make bench-dry: fake models, full
                                       #   report pipeline, zero credits
  python -m bench.run --confirm        # = make bench: real models
  python -m bench.run --estimate-whisper  # time whisper-large-v3 on one clip

- Corpus is FROZEN before the first run: the manifest sha256 goes into the
  report; never drop clips after seeing results.
- Raw transcripts are cached to bench/results/raw/<model>/<clip>.json so
  reruns never re-spend API credits.
- Tier-a audio may arrive as 01.wav..20.wav or case01.wav..case20.wav —
  both resolve; absent case IDs are listed clearly so a partial recording
  session still runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import wave
from pathlib import Path

from sautiledger.config import get_settings  # loads .env for SAHARA_API_KEY
from sautiledger.packs import load_pack

from .metrics import score_clip

BENCH_DIR = Path(__file__).resolve().parent
CORPUS_DIR = BENCH_DIR / "corpus"
RESULTS_DIR = BENCH_DIR / "results"


# ---------------------------------------------------------------- corpus


def _resolve_audio(manifest_dir: Path, clip: dict) -> Path | None:
    """Accept the manifest name plus common variants (01.wav <-> case01.wav)."""
    names = [clip["audio"]]
    m = re.match(r"(?:case)?(\d+)\.wav$", clip["audio"])
    if m:
        num = int(m.group(1))
        names += [f"{num:02d}.wav", f"case{num:02d}.wav", f"{num}.wav"]
    for name in names:
        path = manifest_dir / name
        if path.exists():
            return path
    return None


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
            clip["audio_path"] = _resolve_audio(manifest.parent, clip)
            clips.append(clip)
    return clips, hasher.hexdigest()


def wav_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return 5.0  # non-wav or unreadable: assume a short clip


def clip_seconds(clip: dict) -> float:
    """Prefer the manifest's duration (AfriSwitch publishes it); fall back
    to reading the wav header."""
    duration = clip.get("duration")
    if isinstance(duration, (int, float)) and duration > 0:
        return float(duration)
    return wav_seconds(clip["audio_path"])


# ---------------------------------------------------------------- fake models


def _fake_perfect(text: str) -> str:
    return text


def _fake_anglicised(text: str) -> str:
    """Deterministic 'global model' failure profile: Pidgin grammar broken,
    numbers digitised, meaning inverted."""
    out = text
    for src, dst in [
        ("don sell", "don't sell"),
        ("five thousand five", "5.5k"), ("forty five k", "45k"),
        ("egberun meta", "a thousand meters"), ("abeg", ""), ("oya", ""),
        ("wetin", "what in"), ("nimeuza", "name uza"),
    ]:
        out = out.replace(src, dst)
    return " ".join(out.split())


def _fake_mangler(text: str) -> str:
    """Deterministic amount-corruptor: truncates trailing money words —
    the failure class the transaction metric exists to catch."""
    for src, dst in [
        ("five thousand five", "five thousand"), ("two two fifty", "two fifty"),
        ("one two", "one"), ("egberun meta", "egberun"),
        ("dubu talatin", "dubu"), ("elfu tatu", "elfu"),
        ("mia moja hamsini", "mia moja"),
    ]:
        if src in text:
            return text.replace(src, dst)
    return text


FAKE_MODELS = {
    "FAKE-echo": _fake_perfect,
    "FAKE-anglicised": _fake_anglicised,
    "FAKE-mangler": _fake_mangler,
}


# ---------------------------------------------------------------- whisper timing


def estimate_whisper(clips: list[dict]) -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("faster-whisper not installed — pip install -r bench/requirements.txt")
        return
    sample = next((c for c in clips if c["audio_path"]), None)
    if sample is None:
        import io
        import math
        import struct

        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"".join(
                struct.pack("<h", int(2000 * math.sin(2 * math.pi * 220 * t / 16000)))
                for t in range(80000)
            ))
        sample_path = RESULTS_DIR / "_timing_probe.wav"
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        sample_path.write_bytes(buf.getvalue())
        print("(no corpus audio yet — timing a synthetic 5s clip)")
    else:
        sample_path = sample["audio_path"]

    print("Loading whisper-large-v3 (downloads ~1.5 GB on first run)…")
    t0 = time.perf_counter()
    model = WhisperModel("large-v3", compute_type="int8")
    load_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    segments, _ = model.transcribe(str(sample_path))
    list(segments)  # generator: consume to actually transcribe
    clip_s = time.perf_counter() - t0
    dur = wav_seconds(sample_path)
    n = len([c for c in clips if c["audio_path"]]) or 60
    total_min = (clip_s / max(dur, 0.1)) * sum(
        clip_seconds(c) for c in clips if c["audio_path"]
    ) / 60 if any(c["audio_path"] for c in clips) else (clip_s * n) / 60
    print(f"model load: {load_s:.0f}s; {dur:.1f}s clip took {clip_s:.1f}s "
          f"({clip_s / max(dur, 0.1):.1f}x realtime)")
    print(f"→ estimated whisper-large-v3 wall-clock for the corpus: ~{total_min:.0f} min (+ one-off load)")


# ---------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="actually spend API credits")
    parser.add_argument("--fake", action="store_true", help="dry-run the pipeline with fake models")
    parser.add_argument("--frontier", default="openai", choices=["openai", "gemini", "whisper-small"])
    parser.add_argument("--tier", default=None, help="run one corpus tier only")
    parser.add_argument("--estimate-whisper", action="store_true", help="time whisper on one clip")
    args = parser.parse_args()

    get_settings()  # side effect: loads .env
    clips, manifest_hash = load_corpus()
    if args.tier:
        clips = [c for c in clips if c["tier"] == args.tier]

    present = [c for c in clips if c["audio_path"]]
    missing = [c for c in clips if not c["audio_path"]]
    if missing:
        by_tier: dict[str, list[str]] = {}
        for clip in missing:
            by_tier.setdefault(clip["tier"], []).append(clip["id"])
        for tier, ids in by_tier.items():
            print(f"  ! {tier}: {len(ids)} clips absent -> {', '.join(ids)}")

    if args.estimate_whisper:
        estimate_whisper(clips)
        return

    # spend estimate: every audio tier, per cloud model
    per_tier = {}
    for clip in present:
        per_tier[clip["tier"]] = per_tier.get(clip["tier"], 0) + clip_seconds(clip)
    total_min = sum(per_tier.values()) / 60
    print(f"Corpus: {len(present)}/{len(clips)} clips present, manifest sha256 {manifest_hash[:16]}…")
    for tier, secs in sorted(per_tier.items()):
        print(f"  {tier}: {secs / 60:.1f} audio-min")
    print(f"TOTAL cloud audio per cloud model: {total_min:.1f} minutes")

    if args.fake:
        run_fake(clips, manifest_hash)
        return
    if not present:
        print("No audio present — record clips or run fetch_afriswitch.py first.")
        sys.exit(1)
    if not args.confirm:
        print("Dry run only. Re-run with --confirm to transcribe (or --fake for the report pipeline).")
        sys.exit(0)
    run_real(present, manifest_hash, args.frontier)


def _score(model_name: str, clip: dict, hyp: str) -> dict:
    pack = load_pack(clip.get("language", "pcm-yo-NG"))
    return {
        "model": model_name,
        "clip": clip["id"],
        "tier": clip["tier"],
        "truth": clip["text"],
        "hyp": hyp,
        # wild-speech tiers have no parse ground truth: txn/numeric columns
        # must aggregate only over clips that do (else they read 100% vacuously)
        "has_expected": bool(clip.get("expected_parse")),
        **score_clip(clip["text"], hyp, clip.get("expected_parse") or {}, pack),
    }


def _write_and_report(results: list[dict], manifest_hash: str, notes: list[str],
                      n_present: int, n_missing: int) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "metrics.json").write_text(
        json.dumps({
            "manifest_sha256": manifest_hash,
            "notes": notes,
            "n_clips": n_present,
            "n_missing": n_missing,
            "results": results,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {RESULTS_DIR / 'metrics.json'} ({len(results)} rows)")
    from .report import render

    render()


def run_fake(clips: list[dict], manifest_hash: str) -> None:
    """Report-pipeline proof: fake models transform manifest TEXT (no audio
    needed), so the table structure is visible before any credits are spent."""
    results = [
        _score(name, clip, transform(clip["text"]))
        for name, transform in FAKE_MODELS.items()
        for clip in clips
    ]
    notes = ["DRY RUN: all three models are FAKE text transforms of the ground "
             "truth (echo / anglicised / amount-mangler). Numbers are illustrative "
             "of the table structure only."]
    _write_and_report(results, manifest_hash, notes, len(clips), 0)


def run_real(present: list[dict], manifest_hash: str, frontier: str) -> None:
    from .bench_asr import build_models

    models, notes = build_models(frontier)
    results: list[dict] = []
    for model in models:
        raw_dir = RESULTS_DIR / "raw" / model.name
        raw_dir.mkdir(parents=True, exist_ok=True)
        consecutive_failures = 0
        done = 0
        for clip in present:
            cache = raw_dir / f"{clip['id']}.json"
            if cache.exists():
                hyp = json.loads(cache.read_text(encoding="utf-8"))["transcript"]
            else:
                print(f"[{model.name}] {clip['id']} …", flush=True)
                try:
                    hyp = model.transcribe_file(clip["audio_path"], clip.get("language"))
                    consecutive_failures = 0
                except Exception as exc:
                    consecutive_failures += 1
                    print(f"  ! {type(exc).__name__}: {exc}", flush=True)
                    if consecutive_failures >= 3:
                        # credit exhaustion / outage: stop CLEANLY, never
                        # retry-loop against an empty balance
                        note = (f"{model.name} ABORTED after 3 consecutive failures: "
                                f"{done}/{len(present)} clips completed and cached.")
                        print(f"  !! {note}")
                        notes.append(note)
                        break
                    continue
                cache.write_text(
                    json.dumps({"transcript": hyp, "clip": clip["id"]}, ensure_ascii=False),
                    encoding="utf-8",
                )
            done += 1
            results.append(_score(model.name, clip, hyp))
        print(f"[{model.name}] {done}/{len(present)} clips scored", flush=True)
    _write_and_report(results, manifest_hash, notes, len(present), 0)


if __name__ == "__main__":
    main()
