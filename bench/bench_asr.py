"""Models under test, behind one BenchAsrClient interface.

Cloud models (Sahara, frontier) route through the app's EgressRecorder
into a bench-local DB — the egress-logging rule applies to the benchmark too.
Local whisper models are imported lazily from bench/requirements.txt
installs (NEVER added to the app's dependencies).
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Protocol

from sautiledger.asr import SaharaCloudAsr
from sautiledger.egress import EgressRecorder, encode_multipart
from sautiledger.ledger import Ledger

BENCH_DIR = Path(__file__).resolve().parent


class BenchAsrClient(Protocol):
    name: str

    def transcribe_file(self, path: Path, language_hint: str | None) -> str: ...


def bench_recorder() -> EgressRecorder:
    """All bench cloud traffic is logged here, same as the app's."""
    return EgressRecorder(Ledger(str(BENCH_DIR / "results" / "bench_egress.db")))


class SaharaBench:
    name = "sahara-v2"

    def __init__(self, recorder: EgressRecorder | None = None):
        key = os.environ.get("SAHARA_API_KEY")
        self.client = SaharaCloudAsr(recorder or bench_recorder(), key)

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        return self.client.transcribe(path.read_bytes(), language_hint=language_hint).text


class WhisperLocalBench:
    """faster-whisper, fully local. model_size: 'large-v3' or 'small'."""

    def __init__(self, model_size: str = "large-v3"):
        self.name = f"whisper-{model_size}"
        from faster_whisper import WhisperModel  # bench/requirements.txt only

        self.model = WhisperModel(model_size, compute_type="int8")

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        segments, _info = self.model.transcribe(str(path), language="en")
        return " ".join(s.text.strip() for s in segments).strip()


class OpenAiBench:
    name = "gpt-4o-transcribe"

    def __init__(self, recorder: EgressRecorder | None = None):
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.recorder = recorder or bench_recorder()

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        body, content_type = encode_multipart(
            fields={"model": "gpt-4o-transcribe"},
            files={"file": (path.name, path.read_bytes(), "audio/wav")},
        )
        _status, resp = self.recorder.post(
            "https://api.openai.com/v1/audio/transcriptions",
            purpose=f"benchmark: frontier ASR of {path.name}",
            data=body,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": content_type},
        )
        return json.loads(resp).get("text", "").strip()


class GeminiBench:
    name = "gemini-flash"

    def __init__(self, recorder: EgressRecorder | None = None):
        self.key = os.environ.get("GEMINI_API_KEY")
        if not self.key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self.recorder = recorder or bench_recorder()

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        payload = json.dumps({
            "contents": [{"parts": [
                {"text": "Transcribe this audio verbatim. Return only the transcript."},
                {"inline_data": {
                    "mime_type": "audio/wav",
                    "data": base64.b64encode(path.read_bytes()).decode(),
                }},
            ]}]
        }).encode()
        _status, resp = self.recorder.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={self.key}",
            purpose=f"benchmark: frontier ASR of {path.name}",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        data = json.loads(resp)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def build_models(frontier: str) -> tuple[list, list[str]]:
    """Returns (models, notes). frontier: openai | gemini | whisper-small.
    If no frontier key materialises, whisper-small substitutes and the
    report says so honestly."""
    notes: list[str] = []
    models: list = [SaharaBench(), WhisperLocalBench("large-v3")]
    if frontier == "openai" and os.environ.get("OPENAI_API_KEY"):
        models.append(OpenAiBench())
    elif frontier == "gemini" and os.environ.get("GEMINI_API_KEY"):
        models.append(GeminiBench())
    else:
        models.append(WhisperLocalBench("small"))
        notes.append(
            "No frontier API key was available; whisper-small substitutes as the "
            "third model. This is a weaker baseline than GPT-4o-transcribe/Gemini."
        )
    return models, notes
