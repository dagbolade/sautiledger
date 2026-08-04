"""TTS interface: local implementations only; the cloud stub must refuse."""

from __future__ import annotations

import pytest

from sautiledger.tts import NullTts, PiperLocalTts, SaharaTts, TtsNotAvailable


def test_null_tts_is_silent():
    assert NullTts().speak("Logged: rice, five thousand naira.") == b""


def test_piper_raises_cleanly_when_missing():
    with pytest.raises(TtsNotAvailable):
        PiperLocalTts("voices/nonexistent.onnx", piper_bin="piper-definitely-not-installed")


def test_sahara_tts_refuses_until_egress_wired():
    with pytest.raises(NotImplementedError):
        SaharaTts().speak("hello")
