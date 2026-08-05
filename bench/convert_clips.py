"""Convert phone recordings into the corpus format: 16 kHz mono PCM wav.

Handles anything PyAV can decode (m4a/mp4 AAC voice notes, .opus WhatsApp
notes, ogg, …) — so the Swahili voice notes arriving later go through the
same path. Originals are preserved in a gitignored raw/ subfolder.

Usage:  python -m bench.convert_clips            (= make convert)
        python -m bench.convert_clips --dir bench/corpus/sautiledger-clips
"""

from __future__ import annotations

import argparse
import re
import wave
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent / "corpus" / "sautiledger-clips"
TARGET_RATE = 16000
_CASE_RE = re.compile(r"^(\d+)")


def convert_file(src: Path, dest: Path) -> None:
    import av

    with av.open(str(src)) as container:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="mono", rate=TARGET_RATE)
        chunks: list[bytes] = []
        # to_ndarray() yields exactly frame.samples values; the raw plane
        # buffer includes alignment padding that stretches the audio
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().tobytes())
        for out in resampler.resample(None):  # flush
            chunks.append(out.to_ndarray().tobytes())
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_RATE)
        w.writeframes(b"".join(chunks))


def verify_wav(path: Path) -> tuple[bool, str, float]:
    """Returns (ok, problem, duration_s)."""
    try:
        with wave.open(str(path), "rb") as w:
            rate, channels = w.getframerate(), w.getnchannels()
            frames = w.readframes(w.getnframes())
    except Exception as exc:
        return False, f"unreadable: {exc}", 0.0
    duration = len(frames) / 2 / rate
    if rate != TARGET_RATE:
        return False, f"rate {rate} != {TARGET_RATE}", duration
    if channels != 1:
        return False, f"{channels} channels", duration
    if not 1.0 <= duration <= 15.0:
        return False, f"duration {duration:.1f}s outside 1-15s", duration
    peak = max(
        abs(int.from_bytes(frames[i:i + 2], "little", signed=True))
        for i in range(0, min(len(frames), 2_000_000), 2)
    )
    if peak < 500:  # ~1.5% full scale — a silent/botched take
        return False, f"near-silent (peak {peak})", duration
    return True, "", duration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=str(DEFAULT_DIR))
    args = parser.parse_args()
    corpus = Path(args.dir)
    raw_dir = corpus / "raw"

    sources = [
        p for p in sorted(corpus.iterdir())
        if p.is_file() and p.suffix != ".wav" and _CASE_RE.match(p.name)
        and p.name != "manifest.jsonl"
    ]
    if not sources:
        print(f"nothing to convert in {corpus}")
    for src in sources:
        case_num = int(_CASE_RE.match(src.name).group(1))
        dest = corpus / f"{case_num:02d}.wav"
        convert_file(src, dest)
        raw_dir.mkdir(exist_ok=True)
        src.rename(raw_dir / src.name)
        print(f"converted {src.name} -> {dest.name}")

    print(f"\n{'case':>6}  {'duration':>9}  status")
    problems = 0
    for wav in sorted(corpus.glob("*.wav")):
        ok, problem, duration = verify_wav(wav)
        status = "ok" if ok else f"!! {problem}"
        problems += 0 if ok else 1
        print(f"{wav.stem:>6}  {duration:>8.1f}s  {status}")
    if problems:
        raise SystemExit(f"\n{problems} clip(s) need re-recording")
    print("\nall clips verified")


if __name__ == "__main__":
    main()
