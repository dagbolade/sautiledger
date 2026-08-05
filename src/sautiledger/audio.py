"""Server-side audio normalisation (local only — nothing egresses here).

Browsers send whatever MediaRecorder produces: webm/opus on desktop
Chrome, mp4/AAC on iOS Safari. Sahara 400s on some of these. Every mic
clip is transcoded to a known-good 16 kHz mono PCM wav before the ASR
call, so the cloud always sees one format.
"""

from __future__ import annotations

import io
import wave

TARGET_RATE = 16000
MIN_SECONDS = 0.5  # anything shorter is an accidental button tap


class AudioUnusable(ValueError):
    """Clip could not be decoded, or is too short to contain speech."""


def to_wav16k(blob: bytes) -> tuple[bytes, float]:
    """Returns (wav_bytes, duration_seconds). Raises AudioUnusable."""
    import av

    try:
        chunks: list[bytes] = []
        with av.open(io.BytesIO(blob)) as container:
            stream = container.streams.audio[0]
            resampler = av.AudioResampler(format="s16", layout="mono", rate=TARGET_RATE)
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    chunks.append(bytes(out.planes[0]))
            for out in resampler.resample(None):
                chunks.append(bytes(out.planes[0]))
    except Exception as exc:
        raise AudioUnusable(f"undecodable audio ({type(exc).__name__}: {exc})") from exc

    pcm = b"".join(chunks)
    duration = len(pcm) / 2 / TARGET_RATE
    if duration < MIN_SECONDS:
        raise AudioUnusable(f"clip too short ({duration:.2f}s)")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_RATE)
        w.writeframes(pcm)
    return buf.getvalue(), duration
