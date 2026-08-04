"""Fetch a small code-switched sample from the Intron HuggingFace
collection into bench/corpus/afriswitch-sample/.

HONESTY NOTE: the challenge brief names an "Afriswitch" dataset, but no
dataset by that id exists on HuggingFace at build time. The closest
matches in the intronhealth collection are `intronhealth/afrivox-transcribe`
(the AfriVox benchmark Sahara-v2 reports against) and
`intronhealth/afrispeech-dialog` (code-switched conversations). Default
is afrivox-transcribe; confirm the intended dataset with the Intron crew
and pass --dataset if it differs. Respect the dataset licence
(CC-BY-4.0 for released Intron subsets) — the citation is recorded in
the report.

Usage:
  python -m bench.fetch_afriswitch --confirm            # ~40 clips
  python -m bench.fetch_afriswitch --dataset intronhealth/afrispeech-dialog --confirm

Requires: pip install -r bench/requirements.txt  (datasets, soundfile)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "corpus" / "afriswitch-sample"

# language/accent field values we keep, mapped to our pack names
LANGUAGE_MAP = {
    "pidgin": "pcm-yo-NG",
    "naija": "pcm-yo-NG",
    "yoruba": "pcm-yo-NG",
    "yoruba-english": "pcm-yo-NG",
    "swahili": "sw-KE",
    "swahili-english": "sw-KE",
    "kiswahili": "sw-KE",
    "hausa": "ha-NG",
    "hausa-english": "ha-NG",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="intronhealth/afrivox-transcribe")
    parser.add_argument("--split", default="test")
    parser.add_argument("--max-clips", type=int, default=40)
    parser.add_argument("--confirm", action="store_true", help="actually download")
    args = parser.parse_args()

    if not args.confirm:
        print(f"Would download up to {args.max_clips} clips from {args.dataset} "
              f"({args.split}) into {OUT_DIR}. Re-run with --confirm.")
        return

    import soundfile as sf  # bench deps only
    from datasets import load_dataset

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset(args.dataset, split=args.split, streaming=True)

    kept = 0
    manifest_lines: list[str] = []
    for i, row in enumerate(dataset):
        if kept >= args.max_clips:
            break
        # field names vary across Intron datasets — probe defensively
        lang_raw = str(
            row.get("language") or row.get("accent") or row.get("language_name") or ""
        ).strip().lower()
        pack = LANGUAGE_MAP.get(lang_raw)
        if pack is None:
            continue
        text = (row.get("transcript") or row.get("text") or row.get("sentence") or "").strip()
        audio = row.get("audio")
        if not text or not audio:
            continue
        clip_id = f"afx{kept:03d}"
        wav_path = OUT_DIR / f"{clip_id}.wav"
        sf.write(wav_path, audio["array"], audio["sampling_rate"])
        manifest_lines.append(json.dumps({
            "id": clip_id,
            "audio": wav_path.name,
            "language": pack,
            "source_language_field": lang_raw,
            "source_dataset": args.dataset,
            "source_index": i,
            "text": text,
            "expected_parse": None,  # no ParseResult ground truth for this tier:
                                     # scored on WER + numeric survival only
        }, ensure_ascii=False))
        kept += 1
        print(f"  {clip_id}: [{lang_raw}] {text[:60]}")

    (OUT_DIR / "manifest.jsonl").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"\nWrote {kept} clips + manifest to {OUT_DIR}")
    if kept == 0:
        print("No clips matched the language filter — inspect the dataset's language "
              "field values and extend LANGUAGE_MAP, or try --dataset "
              "intronhealth/afrispeech-dialog.")


if __name__ == "__main__":
    main()
