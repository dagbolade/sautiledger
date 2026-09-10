"""Build an evidence explorer and optionally serve it on localhost.

python -m bench.explorer --serve --port 8094

The static export contains cached benchmark transcripts and scripted replay
results, never application ledgers or audio. The optional LOCAL server can
play existing corpus audio by manifest ID without copying it into the export.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .conversations import evaluate

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "static/benchmark"
CORPUS = ROOT / "bench/corpus"
METRICS = ROOT / "bench/results/metrics.json"
from .publication import LICENSED_TIERS, REDACTION_NOTE, public_row
CONTROLS = {"sahara-v2": "Historical snapshot", "sahara-v2.5-raw": "Ablation control"}


def corpus_index() -> dict[tuple[str, str], dict]:
    index = {}
    for manifest in sorted(CORPUS.glob("*/manifest.jsonl")):
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                clip = json.loads(line)
                index[manifest.parent.name, clip["id"]] = clip
    return index


def build() -> dict:
    cached = json.loads(METRICS.read_text(encoding="utf-8"))
    index = corpus_index()
    clips = {}
    allowed = ("model", "clip", "tier", "truth", "hyp", "has_expected", "wer", "cer",
               "exact_match", "amount_safe", "amount_corrupted", "numeric_accuracy",
               "got_intent", "got_amount", "flags")
    rows = [public_row({k: r.get(k) for k in allowed}) for r in cached["results"]]
    for row in rows:
        if row["tier"] in LICENSED_TIERS:
            row.update(truth="", hyp="", redacted=True)
        key = row["tier"], row["clip"]
        manifest = index.get(key, {})
        clips[key] = {
            "id": row["clip"], "tier": row["tier"], "truth": row["truth"],
            "language": manifest.get("language"),
            "expected": None if row.get("redacted") else manifest.get("expected_parse") or None,
            "redacted": bool(row.get("redacted")),
        }
    conversations = evaluate()
    data = {
        "schema_version": 1,
        "source": {
            "file": "bench/results/metrics.json",
            "sha256": hashlib.sha256(METRICS.read_bytes()).hexdigest(),
            "manifest_sha256": cached.get("manifest_sha256"),
            "declared_clips": cached.get("n_clips"),
            "observed_clips": len(clips),
            "notes": cached.get("notes", []),
            "redaction": REDACTION_NOTE,
        },
        "controls": CONTROLS,
        "clips": sorted(clips.values(), key=lambda c: (c["tier"], c["id"])),
        "asr": rows,
        "conversations": conversations,
    }
    VIEWER.mkdir(parents=True, exist_ok=True)
    (VIEWER / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "bench/results/conversations.json").write_text(
        json.dumps(conversations, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def local_audio() -> dict[tuple[str, str], Path]:
    """Resolve existing manifest audio only, constrained to its corpus folder."""
    from .run import _resolve_audio

    sources = {}
    for key, clip in corpus_index().items():
        folder = (CORPUS / key[0]).resolve()
        path = _resolve_audio(folder, clip)
        if path is not None and path.resolve().is_relative_to(folder):
            sources[key] = path.resolve()
    return sources


def create_explorer_app(audio_enabled: bool = True):
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="SautiLedger local benchmark explorer", docs_url=None, redoc_url=None)
    sources = local_audio() if audio_enabled else {}

    @app.get("/audio-index")
    def audio_index():
        return [{"tier": tier, "clip": clip} for tier, clip in sorted(sources)]

    @app.get("/audio/{tier}/{clip}")
    def audio(tier: str, clip: str):
        path = sources.get((tier, clip))
        if path is None:
            raise HTTPException(404, "No local manifest audio for this clip")
        return FileResponse(path, media_type="audio/wav")

    app.mount("/", StaticFiles(directory=VIEWER, html=True), name="explorer")
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8094)
    parser.add_argument("--no-audio", action="store_true", help="Disable even local corpus playback")
    args = parser.parse_args()
    data = build()
    print(f"Exported {data['source']['observed_clips']} unique clips; source metrics unchanged.")
    print("Static export excludes audio. Conversation results are SCRIPTED text replays.")
    if args.serve:
        import uvicorn
        uvicorn.run(create_explorer_app(not args.no_audio), host="127.0.0.1", port=args.port)
    else:
        print("Open /static/benchmark/index.html in the app, or run again with --serve for local audio.")


if __name__ == "__main__":
    main()
