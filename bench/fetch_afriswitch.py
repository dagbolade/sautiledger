"""Fetch the tier-b sample from intronhealth/AfriSwitch into
bench/corpus/afriswitch-sample/.

AfriSwitch (published Aug 2026): 54.41h / 16,602 code-switched utterances,
14 African languages paired with English, 16kHz audio + ground-truth
`transcription`, per-language configs, test split only.
Licence: CC BY-NC-SA 4.0 — non-commercial benchmark use; citation is
recorded in the report. Nothing from the dataset is committed to the
repo (bench/corpus/ is fetched at run time and gitignored).

GATED DATASET — before running:
  1. Visit https://huggingface.co/datasets/intronhealth/AfriSwitch and
     accept the terms while logged in.
  2. `huggingface-cli login` (or put HF_TOKEN=... in .env).

Usage:
  python -m bench.fetch_afriswitch --confirm         # 40 clips, weighted
  python -m bench.fetch_afriswitch --dataset intronhealth/afrivox-transcribe --confirm

Requires: pip install -r bench/requirements.txt
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "corpus" / "afriswitch-sample"
DEFAULT_DATASET = "intronhealth/AfriSwitch"

# clips per language config — weighted toward Nigerian Pidgin-English and
# Swahili-English per the benchmark spec
WEIGHTS = {"pidgin": 16, "swahili": 12, "yoruba": 6, "hausa": 6}
LANG_TO_PACK = {"pidgin": "pcm-yo-NG", "yoruba": "pcm-yo-NG", "hausa": "ha-NG", "swahili": "sw-KE"}


def _hf_token() -> str | None:
    from sautiledger.config import get_settings

    get_settings()  # loads .env (HF_TOKEN may live there)
    return os.environ.get("HF_TOKEN") or None


def _resolve_config(dataset: str, lang: str, token: str | None) -> str | None:
    from datasets import get_dataset_config_names

    names = get_dataset_config_names(dataset, token=token)
    for name in names:
        if lang.lower() in name.lower():
            return name
    return None


def fetch_afriswitch(dataset: str, max_clips: int) -> None:
    import soundfile as sf
    from datasets import load_dataset

    token = _hf_token()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_lines: list[str] = []
    kept = 0
    scale = max_clips / sum(WEIGHTS.values())

    for lang, weight in WEIGHTS.items():
        want = max(1, round(weight * scale))
        config = _resolve_config(dataset, lang, token)
        if config is None:
            print(f"  ! no config matching '{lang}' — skipping (check config names)")
            continue
        print(f"[{config}] sampling {want} clips…")
        rows = load_dataset(dataset, config, split="test", streaming=True, token=token)
        taken = 0
        for i, row in enumerate(rows):
            if taken >= want:
                break
            text = (row.get("transcription") or "").strip()
            audio = row.get("audio")
            if not text or not audio:
                continue
            clip_id = f"afx{kept:03d}"
            sf.write(OUT_DIR / f"{clip_id}.wav", audio["array"], audio["sampling_rate"])
            manifest_lines.append(json.dumps({
                "id": clip_id,
                "audio": f"{clip_id}.wav",
                "language": LANG_TO_PACK[lang],
                "source_dataset": dataset,
                "source_config": config,
                "source_index": i,
                "source_filename": row.get("filename"),
                "cmi": row.get("cmi"),
                "num_switch_points": row.get("num_switch_points"),
                "duration": row.get("duration"),
                "text": text,
                "expected_parse": None,  # wild speech: scored on WER + numeric survival
            }, ensure_ascii=False))
            kept += 1
            taken += 1
            print(f"  {clip_id}: {text[:70]}")

    (OUT_DIR / "manifest.jsonl").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"\nWrote {kept} clips + manifest to {OUT_DIR}")


def fetch_generic(dataset: str, split: str, max_clips: int) -> None:
    """Fallback path for non-AfriSwitch datasets (e.g. afrivox-transcribe):
    probes common column names for language and transcript."""
    import soundfile as sf
    from datasets import load_dataset

    lang_map = {
        "pidgin": "pcm-yo-NG", "naija": "pcm-yo-NG", "yoruba": "pcm-yo-NG",
        "swahili": "sw-KE", "kiswahili": "sw-KE", "hausa": "ha-NG",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_dataset(dataset, split=split, streaming=True, token=_hf_token())
    manifest_lines: list[str] = []
    kept = 0
    for i, row in enumerate(rows):
        if kept >= max_clips:
            break
        lang_raw = str(row.get("language") or row.get("accent") or "").strip().lower()
        pack = next((p for key, p in lang_map.items() if key in lang_raw), None)
        text = (row.get("transcription") or row.get("transcript") or row.get("text") or "").strip()
        audio = row.get("audio")
        if pack is None or not text or not audio:
            continue
        clip_id = f"afx{kept:03d}"
        sf.write(OUT_DIR / f"{clip_id}.wav", audio["array"], audio["sampling_rate"])
        manifest_lines.append(json.dumps({
            "id": clip_id, "audio": f"{clip_id}.wav", "language": pack,
            "source_dataset": dataset, "source_index": i, "text": text,
            "expected_parse": None,
        }, ensure_ascii=False))
        kept += 1
        print(f"  {clip_id}: [{lang_raw}] {text[:60]}")
    (OUT_DIR / "manifest.jsonl").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"\nWrote {kept} clips + manifest to {OUT_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split", default="test")
    parser.add_argument("--max-clips", type=int, default=40)
    parser.add_argument("--confirm", action="store_true", help="actually download")
    args = parser.parse_args()

    if not args.confirm:
        print(f"Would sample up to {args.max_clips} clips from {args.dataset} into {OUT_DIR}")
        print(f"Weights: {WEIGHTS} (AfriSwitch path). Re-run with --confirm.")
        return
    try:
        if "afriswitch" in args.dataset.lower():
            fetch_afriswitch(args.dataset, args.max_clips)
        else:
            fetch_generic(args.dataset, args.split, args.max_clips)
    except Exception as exc:
        if "gated" in str(exc).lower() or "401" in str(exc) or "403" in str(exc):
            raise SystemExit(
                f"\nGATED dataset: accept the terms at https://huggingface.co/datasets/"
                f"{args.dataset} while logged in, then `huggingface-cli login` or set "
                f"HF_TOKEN in .env, and re-run.\nOriginal error: {exc}"
            )
        raise


if __name__ == "__main__":
    main()
