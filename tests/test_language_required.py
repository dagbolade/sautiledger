"""Intron platform notice, 2026-09-08: from Monday 14 September 08:00 WAT,
"language selection will be required for all Intron ASR and TTS requests…
Requests submitted without a specified language will no longer be processed."

Our four inference call sites already send one. These tests pin that, so a
future refactor cannot quietly drop the parameter and take the app down the
day before submission. Every case asserts a NON-EMPTY value: the failure
mode the notice describes is a missing or blank language, not a wrong one.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from sautiledger.asr import (LANGUAGE_CODES, SaharaAsyncAsr, SaharaCloudAsr,
                             SaharaStreamingAsr)
from sautiledger.egress import EgressRecorder
from sautiledger.ledger import Ledger
from sautiledger.tts import SaharaTts, voice_profile


class CapturingRecorder(EgressRecorder):
    """Records the request body instead of sending it."""

    def __init__(self, response: bytes):
        super().__init__(Ledger(":memory:"),
                         opener=lambda url, data, headers, timeout: (200, response))
        self.sent: list[bytes] = []

    def post(self, url, purpose, data, headers, timeout=30):
        self.sent.append(data)
        return super().post(url, purpose=purpose, data=data, headers=headers, timeout=timeout)

    def get(self, url, purpose, headers=None, timeout=30):
        return 200, b"RIFFfake-wav"

    def open_stream(self, url, purpose, headers, connect=None):
        self.stream_url = url
        return None


def _field(body: bytes, name: str) -> str:
    """Pull one multipart field value out of a captured request body."""
    marker = f'name="{name}"\r\n\r\n'.encode()
    start = body.index(marker) + len(marker)
    return body[start:body.index(b"\r\n--", start)].decode()


# ------------------------------------------------------------ sync ASR

SYNC_OK = json.dumps({"data": {"audio_transcript": "i sell garri"}}).encode()


@pytest.mark.parametrize("hint", [None, "", "pcm-yo-NG", "sw-KE", "sh-ZW", "unknown-pack"])
def test_sync_asr_always_sends_a_language(hint):
    recorder = CapturingRecorder(SYNC_OK)
    SaharaCloudAsr(recorder, api_key="k").transcribe(b"audio", language_hint=hint)
    assert _field(recorder.sent[0], "use_language_asr_input")


def test_sync_asr_sends_the_pack_language_not_a_default():
    recorder = CapturingRecorder(SYNC_OK)
    SaharaCloudAsr(recorder, api_key="k").transcribe(b"audio", language_hint="pcm-yo-NG")
    assert _field(recorder.sent[0], "use_language_asr_input") == "pcm"


def test_unknown_hint_falls_back_to_english_never_to_blank():
    # The fallback is the whole point: an unmapped pack must still send
    # something, because a blank value stops being processed on 14 Sep.
    assert LANGUAGE_CODES.get("no-such-pack", "en") == "en"
    assert all(code for code in LANGUAGE_CODES.values())


# ----------------------------------------------------------- async ASR

ASYNC_OK = json.dumps({"data": {"file_id": "f1"}}).encode()


def test_async_asr_upload_sends_a_language():
    recorder = CapturingRecorder(ASYNC_OK)
    asr = SaharaAsyncAsr(recorder, api_key="k")
    try:
        asr.transcribe(b"audio", language_hint="sw-KE")
    except Exception:
        pass  # polling has nothing to poll here; the upload body is the subject
    assert recorder.sent, "no upload was attempted"
    assert _field(recorder.sent[0], "use_language_asr_input") == "sw"


# -------------------------------------------------------- streaming ASR


def test_streaming_url_carries_a_language_query_parameter():
    recorder = CapturingRecorder(b"")
    SaharaStreamingAsr(recorder, api_key="k").stream()
    url = recorder.stream_url
    values = parse_qs(urlparse(url).query).get("use_language_asr_input")
    assert values and values[0], f"streaming URL has no language: {url}"


def test_streaming_default_language_is_the_product_language():
    recorder = CapturingRecorder(b"")
    SaharaStreamingAsr(recorder, api_key="k").stream()
    assert parse_qs(urlparse(recorder.stream_url).query)["use_language_asr_input"] == ["pcm"]


# ------------------------------------------------------------------ TTS

TTS_OK = json.dumps({"data": {"audio_path": "https://cdn.example/a.wav"}}).encode()


@pytest.mark.parametrize("language,accent", [("pcm", "pidgin"), ("en", "yoruba")])
def test_tts_always_sends_a_voice_language(language, accent):
    recorder = CapturingRecorder(TTS_OK)
    SaharaTts(recorder, api_key="k", language=language, accent=accent).speak("Logged sale.")
    body = json.loads(recorder.sent[0])
    assert body["voice_language"] == language
    assert body["voice_accent"] == accent


@pytest.mark.parametrize("reply_language", ["pcm", "en", "", "anything-else"])
def test_voice_profile_never_yields_a_blank_language(reply_language):
    profile = voice_profile(reply_language)
    assert profile["language"] and profile["accent"] and profile["gender"]
