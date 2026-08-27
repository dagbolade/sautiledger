"""AsrClient interface with cloud, offline, and fake implementations.
The implementation is selected by config, so the on-device engine can
replace the cloud one without touching call sites.

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
    audio without logging it breaks the app's core guarantee."""

    def __init__(self, recorder: EgressRecorder, api_key: str | None, url: str = SAHARA_SYNC_URL):
        if not api_key:
            raise NotConfigured("SAHARA_API_KEY is not set")
        self.recorder = recorder
        self.api_key = api_key
        self.url = url

    def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> Transcript:
        language = LANGUAGE_CODES.get(language_hint or "", "en")
        # audio.py transcodes every clip to 16kHz wav before it reaches here
        body, content_type = encode_multipart(
            fields={
                "audio_file_name": "utterance.wav",
                "use_language_asr_input": language,
            },
            files={"audio_file_blob": ("utterance.wav", audio_bytes, "audio/wav")},
        )
        status, resp = self.recorder.post(
            self.url,
            purpose="your voice clip, sent for transcription",
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": content_type},
        )
        payload = json.loads(resp)
        data = payload.get("data") or {}
        return Transcript(
            text=(data.get("audio_transcript") or "").strip(),
            language_hint=language_hint,
        )


class SaharaAsyncAsr:
    """Alternate cloud path: async upload then poll for the result.
    Same egress rules — the upload is logged with its byte count, and
    every result-check GET is logged at zero bytes. Selected with
    SAUTI_ASR=async (used while the sync endpoint is degraded)."""

    UPLOAD_URL = "https://infer.voice.intron.io/file/v1/upload"
    STATUS_URL = "https://infer.voice.intron.io/file/v1/status/{file_id}"

    def __init__(self, recorder: EgressRecorder, api_key: str | None,
                 poll_interval: float = 2.5, timeout: float = 90.0):
        if not api_key:
            raise NotConfigured("SAHARA_API_KEY is not set")
        self.recorder = recorder
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.timeout = timeout

    def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> Transcript:
        import time

        language = LANGUAGE_CODES.get(language_hint or "", "en")
        body, content_type = encode_multipart(
            fields={
                "audio_file_name": "utterance.wav",
                "use_language_asr_input": language,
            },
            files={"audio_file_blob": ("utterance.wav", audio_bytes, "audio/wav")},
        )
        auth = {"Authorization": f"Bearer {self.api_key}"}
        _status, resp = self.recorder.post(
            self.UPLOAD_URL,
            purpose="your voice clip, sent for transcription",
            data=body,
            headers={**auth, "Content-Type": content_type},
        )
        file_id = (json.loads(resp).get("data") or {}).get("file_id")
        if not file_id:
            return Transcript(text="", language_hint=language_hint)

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            time.sleep(self.poll_interval)
            _status, resp = self.recorder.get(
                self.STATUS_URL.format(file_id=file_id),
                purpose="checking transcription result (no audio sent)",
                headers=auth,
            )
            data = json.loads(resp).get("data") or {}
            state = data.get("processing_status")
            if state == "FILE_TRANSCRIBED":
                return Transcript(
                    text=(data.get("audio_transcript") or "").strip(),
                    language_hint=language_hint,
                )
            if state == "FILE_PROCESSING_FAILED":
                break
        return Transcript(text="", language_hint=language_hint)


class SaharaOfflineAsr:
    """Swap point for Sahara's on-device deployment: drop the local
    engine in here — transcribe() keeps the same signature, call sites
    never change, and the egress meter reads zero."""

    def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> Transcript:
        raise NotImplementedError(
            "Sahara offline engine not yet available — this class is the swap point"
        )


class SaharaStreamingAsr:
    """Live transcription over Sahara's streaming WebSocket
    (docs.voice.intron.io/docs/stt/streaming). This class only speaks the
    message protocol; the connection itself is an egress-logged stream
    from EgressRecorder.open_stream — asr.py never touches the network.

    Contract: base64 PCM16 mono 16 kHz chunks (1-32 KB) as
    INPUT_AUDIO_CHUNK; COMMIT ends the utterance; PARTIAL_TRANSCRIPT
    events arrive as speech is recognised, COMMITTED_TRANSCRIPT carries
    the final text. Max session 300 s.
    """

    URL = "wss://infer.voice.intron.io/stt/v1/stream"
    STREAM_PURPOSE = "your voice, streamed live for transcription"
    COMMIT = json.dumps({"message_type": "COMMIT"})
    _ERRORS = {"INPUT_ERROR", "AUTHENTICATION_ERROR", "RESOURCE_EXHAUSTED",
               "QUOTA_EXCEEDED", "CHUNCK_SIZE_TOO_SMALL", "CHUNK_SIZE_TOO_LARGE",
               "INSUFFICIENT_AUDIO_ACTIVITY", "SESSION_TIME_LIMIT_EXCEEDED"}

    def __init__(self, recorder: EgressRecorder, api_key: str | None,
                 language_code: str = "pcm"):
        if not api_key:
            raise NotConfigured("SAHARA_API_KEY is not set")
        self.recorder = recorder
        self.api_key = api_key
        self.language_code = language_code

    def stream(self, connect=None):
        url = (f"{self.URL}?sample_rate=16000&bit_rate=16&num_channels=1"
               f"&use_language_asr_input={self.language_code}")
        return self.recorder.open_stream(
            url, purpose=self.STREAM_PURPOSE,
            headers={"Authorization": f"Bearer {self.api_key}"},
            connect=connect,
        )

    @staticmethod
    def chunk_message(pcm: bytes, ack_id: int) -> str:
        import base64

        return json.dumps({
            "message_type": "INPUT_AUDIO_CHUNK",
            "audio_base_64": base64.b64encode(pcm).decode("ascii"),
            "ack_id": ack_id,
        })

    @classmethod
    def parse_event(cls, raw) -> tuple[str, str]:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return ("info", "")
        kind = data.get("message_type", "")
        if kind == "PARTIAL_TRANSCRIPT":
            return ("partial", data.get("transcript") or "")
        if kind == "COMMITTED_TRANSCRIPT":
            return ("final", data.get("transcript_text") or "")
        if kind in cls._ERRORS:
            return ("error", kind)
        return ("info", kind)
