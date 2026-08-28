"""Curate consented field-test clips into a submission-ready audio bundle.

Two-step flow, deliberately human-gated:

  1. stage    — match clips from an /admin/audio export against the session's
                usage CSV, copy them into a staging folder under de-identified
                sample ids, and write REVIEW.md (transcripts, staging only)
                so every clip can be eyeballed for personal names.
  2. finalize — zip the staged clips + metadata.csv + CONSENT.md.

finalize REFUSES to run unless every staged session is explicitly named in
--consent-confirmed. The in-app retention consent reads "Clips stay for this
app, nowhere else" — it covers retention for testing, NOT redistribution
into a community benchmark. Fresh, explicit permission from each contributor
is required before a bundle may leave this machine.

Usage:
  python tools/curate_audio_bundle.py stage \
      --clips c6a5b712...-clips.zip --usage c6a5b712...-usage.csv \
      --session c6a5b712abcdef00 --staging bundle-staging
  python tools/curate_audio_bundle.py finalize \
      --staging bundle-staging --out sautiledger-audio-samples.zip \
      --consent-confirmed c6a5b712abcdef00 \
      --consent-note "Contributors re-confirmed sharing with Intron on 2026-09-.."
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import wave
import zipfile
from datetime import date
from pathlib import Path

DOMAIN = "informal-commerce/fintech"
IN_APP_CONSENT = (
    'In-app retention consent (verbatim): "Keep my voice clips make dem help '
    'test the speech model." / "Na only if you gree — you fit off am '
    'anytime. Clips stay for this app, nowhere else."'
)


def _session_ref(session_id: str) -> str:
    # same convention as the statement export: never the raw session id
    return session_id[:4].upper()


def _wav_duration(data: bytes) -> float | None:
    try:
        with wave.open(io.BytesIO(data)) as w:
            return round(w.getnframes() / w.getframerate(), 2)
    except Exception:
        return None


def _load_clips(path: Path) -> dict[str, bytes]:
    """Return {filename: bytes} from a -clips.zip or a directory of clips."""
    clips: dict[str, bytes] = {}
    if path.is_dir():
        for f in sorted(path.iterdir()):
            if f.is_file():
                clips[f.name] = f.read_bytes()
    else:
        with zipfile.ZipFile(path) as z:
            for name in sorted(z.namelist()):
                clips[Path(name).name] = z.read(name)
    return clips


def _load_usage(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def stage(args: argparse.Namespace) -> int:
    staging = Path(args.staging)
    staging.mkdir(parents=True, exist_ok=True)
    manifest_path = staging / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "language": args.language, "device_type": args.device_type, "samples": []}

    clips = _load_clips(Path(args.clips))
    usage_by_clip = {}
    for row in _load_usage(Path(args.usage)):
        if row.get("audio_file"):
            usage_by_clip[Path(row["audio_file"]).name] = row

    ref = _session_ref(args.session)
    existing = {s["source"] for s in manifest["samples"]}
    n = len(manifest["samples"])
    added, skipped = 0, 0
    review_lines = []
    for name, data in clips.items():
        source = f"{args.session}/{name}"
        if source in existing:
            continue
        if not name.endswith(".wav"):
            skipped += 1  # offline .bin captures are not playable samples
            continue
        duration = _wav_duration(data)
        if duration is None:
            skipped += 1
            continue
        n += 1
        sample_id = f"SLA-{n:04d}"
        (staging / f"{sample_id}.wav").write_bytes(data)
        row = usage_by_clip.get(name, {})
        manifest["samples"].append({
            "sample_id": sample_id,
            "session_id": args.session,   # staging only; never enters the bundle
            "session_ref": ref,
            "duration_s": duration,
            "language": args.language,
            "domain": DOMAIN,
            "device_type": args.device_type,
            "outcome": row.get("outcome", ""),
        })
        review_lines.append(
            f"- **{sample_id}** ({duration}s, outcome={row.get('outcome', '?')}): "
            f"{row.get('transcript') or '(no transcript row matched)'}")
        added += 1

    manifest_path.write_text(json.dumps(manifest, indent=2))

    review = staging / "REVIEW.md"
    header = ("# Staged clips — review before finalize\n\n"
              "Read every transcript below and DELETE the .wav of any clip that "
              "names a person or anything else the contributor would not want "
              "shared. This file stays in staging; it is never bundled.\n")
    body = (review.read_text() if review.exists() else header)
    body += f"\n## Session {ref} ({args.session}) — staged {date.today().isoformat()}\n\n"
    body += "\n".join(review_lines) + "\n"
    review.write_text(body)

    print(f"staged {added} clip(s) from session {ref} ({skipped} skipped); "
          f"total staged: {n}")
    print(f"now read {review} and delete any .wav that names a person.")
    return 0


def finalize(args: argparse.Namespace) -> int:
    staging = Path(args.staging)
    manifest = json.loads((staging / "manifest.json").read_text())

    staged_sessions = {s["session_id"] for s in manifest["samples"]}
    confirmed = set(args.consent_confirmed or [])
    missing = staged_sessions - confirmed
    if missing:
        print("REFUSED: the in-app consent says clips 'stay for this app, "
              "nowhere else' — it does not cover sharing in a benchmark bundle.")
        print("Get explicit fresh permission from each contributor, then pass "
              "their session ids via --consent-confirmed:")
        for s in sorted(missing):
            print(f"  missing: {s} (ref {_session_ref(s)})")
        return 1
    if not args.consent_note:
        print("REFUSED: --consent-note is required — record when and how the "
              "contributors gave fresh permission.")
        return 1

    rows, wavs = [], []
    for s in manifest["samples"]:
        wav = staging / f"{s['sample_id']}.wav"
        if not wav.exists():
            continue  # deleted during review — respected
        wavs.append(wav)
        rows.append({k: s[k] for k in ("sample_id", "session_ref", "duration_s",
                                       "language", "domain", "device_type",
                                       "outcome")})

    meta = io.StringIO()
    writer = csv.DictWriter(meta, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

    consent_md = (
        "# Consent\n\n"
        f"{IN_APP_CONSENT}\n\n"
        "That in-app consent authorises retention for model testing only. "
        "For THIS bundle, each contributing tester additionally gave explicit "
        "permission to share their retained clips with Intron for the Sahara "
        "CodeSwitch Africa Challenge community benchmark:\n\n"
        f"> {args.consent_note}\n\n"
        "Samples are de-identified: session references only, no names, no "
        "transcripts. Contributors may withdraw at any time; on withdrawal "
        "their session's samples must be deleted from any copy of this "
        f"bundle.\n\nPackaged {date.today().isoformat()}.\n"
    )

    out = Path(args.out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for wav in wavs:
            z.write(wav, f"audio/{wav.name}")
        z.writestr("metadata.csv", meta.getvalue())
        z.writestr("CONSENT.md", consent_md)
    print(f"wrote {out} — {len(wavs)} sample(s), metadata.csv, CONSENT.md")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    st = sub.add_parser("stage", help="stage one session's clips for review")
    st.add_argument("--clips", required=True,
                    help="-clips.zip from /admin/audio, or a directory")
    st.add_argument("--usage", required=True,
                    help="-usage.csv from /admin/export for the same session")
    st.add_argument("--session", required=True, help="the session id")
    st.add_argument("--language", default="pcm-yo-NG")
    st.add_argument("--device-type", default="smartphone-browser")
    st.add_argument("--staging", default="bundle-staging")
    st.set_defaults(func=stage)

    fi = sub.add_parser("finalize", help="zip the reviewed staging folder")
    fi.add_argument("--staging", default="bundle-staging")
    fi.add_argument("--out", default="sautiledger-audio-samples.zip")
    fi.add_argument("--consent-confirmed", nargs="*",
                    help="session ids whose contributors gave fresh, explicit "
                         "permission to share with Intron")
    fi.add_argument("--consent-note", default="",
                    help="when/how that permission was given (goes in CONSENT.md)")
    fi.set_defaults(func=finalize)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
