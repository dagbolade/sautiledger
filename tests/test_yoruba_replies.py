from fastapi.testclient import TestClient
from sautiledger.api import create_app
from sautiledger.config import Settings
from sautiledger.replies import render_reply
from sautiledger.tts import voice_profile


def test_yoruba_selection_readback_confirmation_and_rejection():
    c=TestClient(create_app(Settings(pack="pcm-yo-NG",db_path=":memory:",mode="offline",agent="none",sahara_api_key=None)))
    assert c.post("/language",data={"speech_pack":"pcm-yo-NG","reply_language":"yo"}).status_code==200
    def say(text):return c.post("/utterance",data={"text":text}).json()
    r=say("I sell 2 cup of rice for 500 naira each")
    assert "Ṣé ó tọ́?" in r["reply_text"]
    assert "five hundred naira each" in r["reply_text"]
    assert "one thousand naira total" in r["reply_text"]
    assert r["review"]["status"]=="recorded_awaiting_confirmation"
    assert "Àkọsílẹ̀" in say("Bẹ́ẹ̀ ni")["reply_text"]
    say("I buy fuel for 2000 naira")
    assert "yọ" in say("Rárá")["reply_text"]
    state=c.get("/state").json()
    assert state["reply_language"]=="yo" and not state["retain_audio"]
    assert state["voice"]["language"]=="yo"


def test_yoruba_voice_and_safe_english_fallback():
    assert voice_profile("yo","hausa","male")=={"language":"yo","accent":"yoruba","gender":"male"}
    assert render_reply("Unknown safety message: 500 naira", "yo")=="Unknown safety message: 500 naira"
    assert render_reply("Wetin she buy? Talk the thing name.","yo")=="Kí ni orúkọ ọjà náà?"
