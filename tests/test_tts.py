"""TTS interface: local implementations only; the cloud stub must refuse."""

from __future__ import annotations

import pytest

from sautiledger.tts import NullTts, PiperLocalTts, SaharaTts, TtsNotAvailable


def test_null_tts_is_silent():
    assert NullTts().speak("Logged: rice, five thousand naira.") == b""


def test_piper_raises_cleanly_when_missing():
    with pytest.raises(TtsNotAvailable):
        PiperLocalTts("voices/nonexistent.onnx", piper_bin="piper-definitely-not-installed")


def test_sahara_tts_cannot_be_built_without_a_recorder():
    """The condition the old guard test waited for is now met: Sahara TTS
    is wired THROUGH egress. The constructor makes the recorder mandatory,
    so an unlogged cloud voice call cannot even be instantiated."""
    with pytest.raises(TypeError):
        SaharaTts()


# ------------------------------------------------- Sahara Pidgin voice


def test_sahara_tts_routes_both_calls_through_egress():
    import json

    from sautiledger.egress import EgressRecorder
    from sautiledger.ledger import Ledger
    from sautiledger.tts import SaharaTts

    calls = []

    def fake_open(url, data, headers, timeout, method="POST"):
        calls.append((method, url))
        if method == "POST":
            return 200, json.dumps({"data": {
                "audio_path": "http://bucket.s3.amazonaws.com/voice.wav",
                "processing_status": "TTS_TEXT_AUDIO_GENERATED"}}).encode()
        return 200, b"RIFFfakewav"

    recorder = EgressRecorder(Ledger(":memory:"), opener=fake_open)
    tts = SaharaTts(recorder, api_key="key")
    audio = tts.speak("Logged: crayfish, two thousand naira. Correct?")

    assert audio == b"RIFFfakewav"
    assert calls[0][0] == "POST" and "tts/v1/generate" in calls[0][1]
    assert calls[1][0] == "GET" and calls[1][1].startswith("https://")  # scheme upgraded
    log = recorder.log()
    assert len(log) == 2  # generate + fetch, both in the transmission ledger
    purposes = {r["purpose"] for r in log}
    assert "your reply, sent to make the voice" in purposes
    assert "fetching the voice audio" in purposes


def test_tts_endpoint_degrades_to_browser_voice_offline():
    from fastapi.testclient import TestClient

    from sautiledger.api import create_app
    from sautiledger.config import Settings

    client = TestClient(create_app(Settings(
        pack="pcm-yo-NG", db_path=":memory:", mode="offline", sahara_api_key=None)))
    assert client.get("/state").json()["tts"] == "browser"
    assert client.post("/tts", data={"text": "hello"}).status_code == 204
