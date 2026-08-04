"""AsrClient interface with cloud, offline, and fake implementations
(CLAUDE.md rule 6: offline-swappable, selected by config).

Sahara API contract (docs.voice.intron.io/docs/stt/file-upload-sync):
  POST https://infer.voice.intron.io/file/v1/upload/sync
  Authorization: Bearer <key>; multipart form-data with
  audio_file_name, audio_file_blob, use_language_asr_input (default en).
  Response: {"data": {"audio_transcript": ..., "processing_status":
  "FILE_TRANSCRIBED", ...}}. Max 120s audio, 30 requests/min.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .egress import EgressRecorder, encode_multipart
from .models import Transcript

SAHARA_SYNC_URL = "https://infer.voice.intron.io/file/v1/upload/sync"

# Sahara language codes (docs.voice.intron.io/docs/stt/supported-languages):
# Pidgin-English=pcm, Yoruba-English=yo, Hausa-English=ha, Swahili-English=sw.
# The mixed pcm-yo-NG pack maps to pcm (Sahara's strongest Pidgin model);
# pass "yo" per-clip for Yoruba-dominant audio if it benchmarks better.
LANGUAGE_CODES = {"pcm-yo-NG": "pcm", "sw-KE": "sw", "ha-NG": "ha"}


class NotConfigured(RuntimeError):
    """ASR implementation selected but missing configuration (e.g. API key)."""


class AsrClient(Protocol):
    def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> Transcript: ...


class FakeAsr:
    """Test/dev ASR: fixture filenames map to spec utterances, and raw
    UTF-8 text bytes pass straight through (lets the dev UI 'record' text)."""

    def __init__(self, fixtures: dict[str, str] | None = None):
        self.fixtures = fixtures or _spec_fixtures()

    def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> Transcript:
        try:
            text = audio_bytes.decode("utf-8")
            if text.strip() and text.isprintable():
                return Transcript(text=self.fixtures.get(text.strip(), text.strip()),
                                  language_hint=language_hint)
        except UnicodeDecodeError:
            pass
        return Transcript(text="", language_hint=language_hint)


def _spec_fixtures() -> dict[str, str]:
    """caseNN.wav -> utterance, from the source-of-truth test file."""
    spec_path = Path(__file__).resolve().parents[2] / "normaliser_tests.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    return {f"case{c['id']:02d}.wav": c["utterance"] for c in spec["cases"]}


class SaharaCloudAsr:
    """Cloud ASR. The ONLY data that ever leaves the device is the audio
    clip sent here, and it goes through the egress recorder — sending
    audio without logging it violates CLAUDE.md rule 2."""

    def __init__(self, recorder: EgressRecorder, api_key: str | None, url: str = SAHARA_SYNC_URL):
        if not api_key:
            raise NotConfigured("SAHARA_API_KEY is not set")
        self.recorder = recorder
        self.api_key = api_key
        self.url = url

    def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> Transcript:
        language = LANGUAGE_CODES.get(language_hint or "", "en")
        body, content_type = encode_multipart(
            fields={
                "audio_file_name": "utterance.webm",
                "use_language_asr_input": language,
            },
            files={"audio_file_blob": ("utterance.webm", audio_bytes, "audio/webm")},
        )
        status, resp = self.recorder.post(
            self.url,
            purpose=f"ASR transcription of one voice clip ({len(audio_bytes)} audio bytes)",
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": content_type},
        )
        payload = json.loads(resp)
        data = payload.get("data") or {}
        return Transcript(
            text=(data.get("audio_transcript") or "").strip(),
            language_hint=language_hint,
        )


class SaharaOfflineAsr:
    """Swap point for Sahara's on-device deployment: drop the local
    engine in here — transcribe() keeps the same signature, call sites
    never change, and the egress meter reads zero."""

    def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> Transcript:
        raise NotImplementedError(
            "Sahara offline engine not yet available — this class is the swap point"
        )
