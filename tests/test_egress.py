"""The egress recorder: every transmission logged, success or failure."""

from __future__ import annotations

import pytest

from sautiledger.egress import EgressError, EgressRecorder, encode_multipart
from sautiledger.ledger import Ledger


def test_successful_post_is_logged():
    ledger = Ledger(":memory:")
    recorder = EgressRecorder(ledger, opener=lambda url, data, headers, timeout: (200, b"{}"))
    status, body = recorder.post(
        "https://infer.voice.intron.io/file/v1/upload/sync",
        purpose="ASR transcription of one voice clip",
        data=b"x" * 1234,
        headers={},
    )
    assert status == 200
    rows = recorder.log()
    assert len(rows) == 1
    row = rows[0]
    assert row["destination"] == "infer.voice.intron.io"
    assert row["bytes_sent"] == 1234
    assert "HTTP 200" in row["disposition"]
    assert recorder.total_bytes() == 1234


def test_failed_post_is_still_logged():
    def exploding(url, data, headers, timeout):
        raise OSError("network unreachable")

    ledger = Ledger(":memory:")
    recorder = EgressRecorder(ledger, opener=exploding)
    with pytest.raises(EgressError):
        recorder.post("https://example.com/x", purpose="test", data=b"abc", headers={})
    rows = recorder.log()
    assert len(rows) == 1
    assert rows[0]["disposition"].startswith("send failed")
    assert rows[0]["bytes_sent"] == 3


def test_multipart_encoding_roundtrip():
    body, content_type = encode_multipart(
        fields={"audio_file_name": "clip.webm"},
        files={"audio_file_blob": ("clip.webm", b"\x00\x01audio", "audio/webm")},
    )
    assert content_type.startswith("multipart/form-data; boundary=")
    boundary = content_type.split("boundary=")[1]
    assert f"--{boundary}".encode() in body
    assert b'name="audio_file_name"' in body
    assert b'filename="clip.webm"' in body
    assert b"\x00\x01audio" in body
    assert body.endswith(f"--{boundary}--\r\n".encode())
