"""Audio transcode: duration must be preserved. A resampler that copies
plane padding stretches clips (~1.26x observed) into garbage for every
ASR model — this regression test pins the fix."""

from __future__ import annotations

import io
import math
import struct
import wave

import pytest

from sautiledger.audio import AudioUnusable, to_wav16k


def _tone_wav(seconds: float, rate: int = 48000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * t / rate)))
            for t in range(int(seconds * rate))
        ))
    return buf.getvalue()


def test_duration_preserved_across_resample():
    src = _tone_wav(3.0, rate=48000)
    wav, duration = to_wav16k(src)
    assert abs(duration - 3.0) < 0.06  # no time-stretch
    with wave.open(io.BytesIO(wav), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        assert abs(w.getnframes() / 16000 - 3.0) < 0.06


def test_too_short_clip_rejected():
    with pytest.raises(AudioUnusable):
        to_wav16k(_tone_wav(0.2))


def test_garbage_bytes_rejected():
    with pytest.raises(AudioUnusable):
        to_wav16k(b"not audio at all")
