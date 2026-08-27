"""TtsClient interface — implementations selected by config.

Default voice-out path is the BROWSER's speechSynthesis (static/app.js):
fully on-device, zero egress, zero install. Trade-off (see README):
voice quality is robotic-ish, but the readback's job is verification,
not beauty — the trader hears the amount echoed back.

PiperLocalTts is here for a nicer local voice when a piper binary and
voice model are installed. SaharaTts is the swap point for Intron's TTS;
NOTE: a CLOUD TTS call would send reply text off-device, breaking the
audio-only egress guarantee — if ever enabled it MUST route through
egress.py so the meter shows it.
"""

from __future__ import annotations

import json
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
    """Intron's Sahara TTS — a real Pidgin voice for the readback.

    The reply text echoes ledger amounts, so every call is a transmission:
    both the generate POST and the audio fetch route through
    EgressRecorder and appear in the transmission ledger. Verified
    contract: voice_language "pcm" + voice_accent "pidgin"; the response
    carries an audio_path URL to fetch.
    """

    URL = "https://infer.voice.intron.io/tts/v1/generate"

    def __init__(self, recorder, api_key: str, gender: str = "female",
                 language: str = "pcm", accent: str = "pidgin"):
        self.recorder = recorder
        self.api_key = api_key
        self.gender = gender
        self.language = language
        self.accent = accent

    def speak(self, text: str) -> bytes:
        body = json.dumps({
            "text": text[:1000],
            "voice_language": self.language,
            "voice_accent": self.accent,
            "voice_gender": self.gender,
        }).encode("utf-8")
        _status, resp = self.recorder.post(
            self.URL,
            purpose="your reply, sent to make the voice",
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            timeout=60,
        )
        audio_url = json.loads(resp)["data"]["audio_path"]
        if audio_url.startswith("http://"):
            audio_url = "https://" + audio_url[len("http://"):]
        _status, audio = self.recorder.get(
            audio_url, purpose="fetching the voice audio", headers={}, timeout=60
        )
        return audio
