"""TtsClient interface (CLAUDE.md rule 6: swappable by config).

Default voice-out path is the BROWSER's speechSynthesis (static/app.js):
fully on-device, zero egress, zero install. Trade-off (see README):
voice quality is robotic-ish, but the readback's job is verification,
not beauty — the trader hears the amount echoed back.

PiperLocalTts is here for a nicer local voice when a piper binary and
voice model are installed. SaharaTts is the swap point for Intron's TTS;
NOTE: a CLOUD TTS call would send reply text off-device — that violates
CLAUDE.md rule 1 unless the pitch changes, and it MUST route through
egress.py so the meter shows it.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol


class TtsNotAvailable(RuntimeError):
    pass


class TtsClient(Protocol):
    def speak(self, text: str) -> bytes:
        """Return audio bytes (wav) for the given text."""
        ...


class NullTts:
    """Silence — used in tests and when the browser handles voice-out."""

    def speak(self, text: str) -> bytes:
        return b""


class PiperLocalTts:
    """Local neural TTS via the `piper` CLI. Fully offline.

    Install: https://github.com/rhasspy/piper — download a voice model
    (e.g. en_US-lessac-medium.onnx) into voices/ and pass its path.
    """

    def __init__(self, voice_model: str | Path, piper_bin: str = "piper"):
        if shutil.which(piper_bin) is None:
            raise TtsNotAvailable(f"'{piper_bin}' not found on PATH")
        self.voice_model = str(voice_model)
        self.piper_bin = piper_bin

    def speak(self, text: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.wav"
            subprocess.run(
                [self.piper_bin, "--model", self.voice_model, "--output_file", str(out)],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            return out.read_bytes()


class SaharaTts:
    """Swap point for Intron's Sahara TTS (docs.voice.intron.io/docs/tts/*).

    Deliberately unimplemented: cloud TTS would transmit the reply text
    (which echoes ledger amounts) off-device — a rule 1 violation unless
    the sovereignty story changes. If ever enabled, the request MUST go
    through egress.EgressRecorder so the transmission ledger shows it.
    """

    def speak(self, text: str) -> bytes:
        raise NotImplementedError(
            "Sahara TTS not enabled: cloud TTS would egress ledger contents (rule 1). "
            "Wire through egress.EgressRecorder if the pitch ever changes."
        )
