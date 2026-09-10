import json

import pytest
from fastapi.testclient import TestClient

from sautiledger.api import create_app
from sautiledger.config import Settings
from sautiledger.tts import voice_profile, SaharaTts
from bench.publication import public_row


def test_redaction_preserves_scores_and_owned_transcripts():
    row = {"tier": "afriswitch-sample", "truth": "licensed reference", "hyp": "licensed hypothesis", "wer": 0.25, "cer": 0.1, "model": "test"}
    public = public_row(row)
    assert public == {**row, "truth": "", "hyp": "", "redacted": True}
    assert row["truth"] == "licensed reference"
    own = {**row, "tier": "sh-clips"}
    assert public_row(own) == own


def test_public_explorer_redacts_even_an_unredacted_source(tmp_path, monkeypatch):
    import bench.explorer as explorer
    root = tmp_path
    (root / "bench/results").mkdir(parents=True)
    metrics = root / "bench/results/metrics.json"
    metrics.write_text(json.dumps({"results": [
        {"tier":"afriswitch-sample", "clip":"broadcast", "truth":"licensed reference", "hyp":"licensed hypothesis", "wer":0.3},
        {"tier":"sh-clips", "clip":"owned", "truth":"own reference", "hyp":"own hypothesis", "wer":0.1},
    ]}))
    monkeypatch.setattr(explorer, "ROOT", root)
    monkeypatch.setattr(explorer, "VIEWER", root / "static/benchmark")
    monkeypatch.setattr(explorer, "METRICS", metrics)
    monkeypatch.setattr(explorer, "corpus_index", lambda: {("afriswitch-sample", "broadcast"): {"expected_parse": {"item":"licensed item"}}})
    monkeypatch.setattr(explorer, "evaluate", lambda: {})
    before = metrics.read_bytes()
    data = explorer.build()
    published = json.dumps(data)
    assert "licensed reference" not in published and "licensed hypothesis" not in published
    assert "licensed item" not in published
    assert "own reference" in published and "own hypothesis" in published
    assert data["asr"][0]["wer"] == 0.3
    assert metrics.read_bytes() == before


def test_voice_profiles_follow_reply_language():
    assert voice_profile("en") == {"language":"en", "accent":"yoruba", "gender":"female"}
    assert voice_profile("pcm", "hausa", "male") == {"language":"pcm", "accent":"pidgin", "gender":"male"}
    with pytest.raises(ValueError):
        voice_profile("en", "shona")  # not documented as an English accent


def test_voice_cache_varies_by_language_accent_and_gender(tmp_path, monkeypatch):
    import sautiledger.api as api
    calls = []
    class FakeVoice:
        def __init__(self, recorder, key, **profile):
            self.profile = profile
        def speak(self, text):
            calls.append((self.profile, text))
            return b"RIFFtest"
    monkeypatch.setattr(api, "SaharaTts", FakeVoice)
    settings = Settings(pack="pcm-yo-NG", db_path=str(tmp_path / "app.db"), mode="cloud", sahara_api_key="fake", agent="none")
    client = TestClient(create_app(settings))
    assert client.get("/state").json()["tts"] == "sahara"
    # pcm-yo-NG now answers in Pidgin by default; this test is about the
    # ENGLISH voice profile, so select English explicitly rather than
    # relying on whatever the default happens to be.
    client.post("/language", data={"speech_pack": "pcm-yo-NG", "reply_language": "en"})
    def play():
        assert client.post("/tts", data={"text":"Please check the rice sale. Correct?"}).status_code == 200
    play(); play()
    assert len(calls) == 1 and calls[0][0]["accent"] == "yoruba"
    assert client.post("/voice", data={"accent":"igbo", "gender":"male"}).status_code == 200
    play(); play()
    assert len(calls) == 2 and calls[-1][0] == {"language":"en", "accent":"igbo", "gender":"male"}
    client.post("/language", data={"speech_pack":"pcm-yo-NG", "reply_language":"pcm"})
    play()
    assert calls[-1][0]["language"] == "pcm" and calls[-1][0]["accent"] == "pidgin"
    restored = TestClient(create_app(settings)); restored.cookies.update(client.cookies)
    assert restored.get("/state").json()["voice"]["gender"] == "male"
    assert not restored.get("/state").json()["retain_audio"]
    assert client.post("/voice", data={"accent":"invented", "gender":"male"}).status_code == 400


def test_long_reply_is_rejected_instead_of_losing_the_confirmation():
    class Recorder:
        def post(self, *args, **kwargs):
            pytest.fail("Long text should never be transmitted or silently truncated")
    with pytest.raises(ValueError):
        SaharaTts(Recorder(), "fake").speak("x" * 4097 + " Correct?")
