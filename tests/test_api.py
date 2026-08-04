"""FastAPI endpoint tests — offline mode, FakeAsr, in-memory DB."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sautiledger.api import create_app
from sautiledger.asr import FakeAsr
from sautiledger.config import Settings


@pytest.fixture
def client():
    app = create_app(
        Settings(pack="pcm-yo-NG", db_path=":memory:", mode="offline", sahara_api_key=None)
    )
    return TestClient(app)


def test_text_utterance_logs_and_reports_zero_egress(client):
    resp = client.post(
        "/utterance", data={"text": "I don sell three derica of rice five thousand five"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "five thousand five hundred naira" in body["reply_text"]
    assert body["egress_delta"] == 0
    assert body["egress_total"] == 0


def test_audio_upload_via_fake_asr(client):
    # FakeAsr maps fixture names to spec utterances (case05 = "sell garri egberun meta")
    resp = client.post(
        "/utterance",
        files={"audio": ("clip.webm", b"case05.wav", "audio/webm")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"] == "sell garri egberun meta"
    assert "three thousand naira" in body["reply_text"]
    assert body["egress_total"] == 0  # offline mode: nothing left the device


def test_empty_request_is_rejected(client):
    assert client.post("/utterance", data={"text": "  "}).status_code == 400


def test_state_endpoint(client):
    client.post("/utterance", data={"text": "sell garri egberun meta"})
    state = client.get("/state").json()
    assert state["mode"] == "offline"
    assert state["sales_total"] == 3000
    assert state["egress_total"] == 0
    assert state["egress_log"] == []


def test_fake_asr_fixture_map():
    fake = FakeAsr()
    assert fake.transcribe(b"case20.wav").text == "log am make I hear"
