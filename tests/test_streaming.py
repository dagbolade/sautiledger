"""Live streaming voice: the egress-logged WebSocket channel, the Sahara
streaming protocol client, and the /stream relay endpoint end-to-end."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import sautiledger.api as api_mod
from sautiledger.api import create_app
from sautiledger.asr import SaharaStreamingAsr
from sautiledger.config import Settings
from sautiledger.egress import EgressError, EgressRecorder
from sautiledger.ledger import Ledger


# ------------------------------------------------- LoggedStream (egress)


def test_logged_stream_measures_and_finalises():
    class FakeWs:
        async def send(self, data): pass
        async def recv(self): return "PONG!"
        async def close(self): pass

    async def fake_connect(url, headers):
        return FakeWs()

    rec = EgressRecorder(Ledger(":memory:"))

    async def run():
        async with rec.open_stream("wss://x.example/ws", purpose="test stream",
                                   headers={}, connect=fake_connect) as stream:
            assert rec.log()[0]["disposition"] == "stream in progress"
            await stream.send(b"abcd")
            await stream.send("efgh")
            await stream.recv()

    asyncio.run(run())
    row = rec.log()[0]
    assert row["bytes_sent"] == 8
    assert row["destination"] == "x.example"
    assert "stream closed" in row["disposition"]
    assert "5 bytes received" in row["disposition"]


def test_logged_stream_failure_still_leaves_a_record():
    async def failing_connect(url, headers):
        raise OSError("no route")

    rec = EgressRecorder(Ledger(":memory:"))

    async def run():
        with pytest.raises(EgressError):
            async with rec.open_stream("wss://x.example/ws", purpose="test stream",
                                       headers={}, connect=failing_connect):
                pass

    asyncio.run(run())
    assert "failed to open" in rec.log()[0]["disposition"]


# ------------------------------------------------- protocol client


def test_streaming_protocol_messages():
    msg = json.loads(SaharaStreamingAsr.chunk_message(b"\x01\x02", 7))
    assert msg["message_type"] == "INPUT_AUDIO_CHUNK"
    assert msg["ack_id"] == 7
    assert msg["audio_base_64"] == "AQI="
    assert json.loads(SaharaStreamingAsr.COMMIT) == {"message_type": "COMMIT"}

    assert SaharaStreamingAsr.parse_event(
        '{"message_type": "PARTIAL_TRANSCRIPT", "transcript": "i don"}'
    ) == ("partial", "i don")
    assert SaharaStreamingAsr.parse_event(
        '{"message_type": "COMMITTED_TRANSCRIPT", "transcript_text": "i don sell"}'
    ) == ("final", "i don sell")
    assert SaharaStreamingAsr.parse_event(
        '{"message_type": "QUOTA_EXCEEDED"}'
    )[0] == "error"
    assert SaharaStreamingAsr.parse_event(
        '{"message_type": "SESSION_CREATED", "session_id": "x"}'
    )[0] == "info"


# ------------------------------------------------- /stream relay endpoint


class _FakeUp:
    """Scripted Sahara side: one partial immediately, final after COMMIT."""

    def __init__(self):
        self.committed = asyncio.Event()
        self.partial_sent = False
        self.audio_chunks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def send(self, data):
        if "COMMIT" in data:
            self.committed.set()
        else:
            self.audio_chunks += 1

    async def recv(self):
        if not self.partial_sent:
            self.partial_sent = True
            return json.dumps({"message_type": "PARTIAL_TRANSCRIPT",
                               "transcript": "i don sell"})
        await self.committed.wait()
        return json.dumps({"message_type": "COMMITTED_TRANSCRIPT",
                           "transcript_text": "i don sell 3 crayfish for 2000 naira",
                           "audio_len": 1.0})


class _FakeSasr:
    STREAM_PURPOSE = SaharaStreamingAsr.STREAM_PURPOSE
    COMMIT = SaharaStreamingAsr.COMMIT
    chunk_message = staticmethod(SaharaStreamingAsr.chunk_message)
    parse_event = staticmethod(SaharaStreamingAsr.parse_event)

    last = None

    def __init__(self, recorder, api_key, language_code="pcm"):
        self.up = _FakeUp()
        _FakeSasr.last = self

    def stream(self, connect=None):
        return self.up


def test_stream_endpoint_relays_partials_and_logs_the_turn(monkeypatch):
    monkeypatch.setattr(api_mod, "SaharaStreamingAsr", _FakeSasr)
    app = create_app(Settings(pack="pcm-yo-NG", db_path=":memory:",
                              mode="cloud", sahara_api_key="key"))
    client = TestClient(app)
    device = None
    client.get("/state")
    device = client.cookies.get("sauti_device")

    with client.websocket_connect(
        "/stream", headers={"cookie": f"sauti_device={device}"}
    ) as ws:
        assert ws.receive_json() == {"type": "partial", "text": "i don sell"}
        ws.send_bytes(b"\x00\x01" * 4096)  # 8 KB of PCM
        ws.send_text(json.dumps({"type": "stop"}))
        final = ws.receive_json()

    assert final["type"] == "final"
    assert final["transcript"] == "i don sell 3 crayfish for 2000 naira"
    assert "two thousand naira" in final["reply_text"]
    assert _FakeSasr.last.up.audio_chunks == 1

    state = client.get("/state").json()
    assert state["sales_total"] == 2000
    assert [e["item"] for e in state["entries"]] == ["crayfish"]


def test_stream_endpoint_unavailable_offline():
    app = create_app(Settings(pack="pcm-yo-NG", db_path=":memory:",
                              mode="offline", sahara_api_key=None))
    client = TestClient(app)
    with client.websocket_connect("/stream") as ws:
        assert ws.receive_json() == {"type": "unavailable"}


class _CommitBugUp(_FakeUp):
    """Sahara's current behavior: partials flow, then COMMIT is answered
    with INPUT_ERROR instead of COMMITTED_TRANSCRIPT."""

    async def recv(self):
        if not self.partial_sent:
            self.partial_sent = True
            return json.dumps({"message_type": "PARTIAL_TRANSCRIPT",
                               "transcript": "i don sell 3 crayfish for 2000 naira"})
        await self.committed.wait()
        return json.dumps({"message_type": "INPUT_ERROR",
                           "message": "Error processing data"})


def test_commit_bug_falls_back_to_last_partial(monkeypatch):
    class Sasr(_FakeSasr):
        def __init__(self, recorder, api_key, language_code="pcm"):
            self.up = _CommitBugUp()
            _FakeSasr.last = self

    monkeypatch.setattr(api_mod, "SaharaStreamingAsr", Sasr)
    app = create_app(Settings(pack="pcm-yo-NG", db_path=":memory:",
                              mode="cloud", sahara_api_key="key"))
    client = TestClient(app)
    client.get("/state")
    device = client.cookies.get("sauti_device")

    with client.websocket_connect(
        "/stream", headers={"cookie": f"sauti_device={device}"}
    ) as ws:
        assert ws.receive_json()["type"] == "partial"
        ws.send_bytes(b"\x00\x01" * 4096)
        ws.send_text(json.dumps({"type": "stop"}))
        final = ws.receive_json()

    assert final["type"] == "final"
    assert final["transcript"] == "i don sell 3 crayfish for 2000 naira"
    assert client.get("/state").json()["sales_total"] == 2000
