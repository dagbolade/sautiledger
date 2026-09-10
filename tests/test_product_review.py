import json

from fastapi.testclient import TestClient

from sautiledger.api import create_app
from sautiledger.config import Settings
from bench.conversations import DEFAULT_SCENARIOS, run_scenario, wrong_amount_count
from bench.explorer import create_explorer_app


def app(db=":memory:"):
    return create_app(Settings(pack="pcm-yo-NG", db_path=db, mode="offline", agent="none", sahara_api_key=None))


def say(client, text):
    return client.post("/utterance", data={"text": text}).json()


def choose(client, pack="pcm-yo-NG", reply="en"):
    return client.post("/language", data={"speech_pack": pack, "reply_language": reply})


def test_review_restores_and_corrected_amount_can_be_rejected():
    shared = app()
    client, other = TestClient(shared), TestClient(shared)
    pending = say(client, "I don sell garri finish")
    assert pending["review"]["status"] == "not_recorded"
    assert pending["review"]["transaction"]["amount"] is None
    assert "raw_utterance" not in pending["review"]["transaction"]
    assert client.get("/state").json()["review_reply"] == pending["reply_text"]
    assert other.get("/state").json()["review"] is None
    assert choose(client, reply="pcm").status_code == 409
    logged = say(client, "five thousand")
    assert logged["review"]["status"] == "recorded_awaiting_confirmation"
    corrected = say(client, "no no na six thousand")
    assert corrected["review"]["transaction"]["amount"] == 6000
    assert corrected["review"]["status"] == "recorded_awaiting_confirmation"
    say(client, "no")
    state = client.get("/state").json()
    assert state["sales_total"] == 0
    assert state["review"] is None


def test_language_is_scoped_persisted_and_currency_cannot_mix(tmp_path):
    database = str(tmp_path / "languages.db")
    shared = app(database)
    shona, nigeria = TestClient(shared), TestClient(shared)
    assert choose(shona, "sh-ZW").status_code == 200
    assert shona.get("/state").json()["currency"] == "USD"
    assert nigeria.get("/state").json()["currency"] == "NGN"
    reply = say(shona, "Ndatengesa matomatisi ethree dollars")
    assert reply["review"]["transaction"]["amount"] == 300
    assert "three dollars" in reply["reply_text"]
    say(shona, "yes")
    assert choose(shona).status_code == 409
    restored = TestClient(app(database))
    restored.cookies.update(shona.cookies)
    assert restored.get("/state").json()["pack"] == "sh-ZW"
    assert "USD" in restored.get("/statement").text or "$" in restored.get("/statement").text
    assert not restored.get("/state").json()["retain_audio"]
    assert choose(nigeria, reply="pcm").status_code == 200
    assert say(nigeria, "hello")["reply_text"].startswith("Wetin")
    say(nigeria, "I sell rice for 5000 naira")
    say(nigeria, "yes")
    assert choose(nigeria).status_code == 200
    assert "What would you" in say(nigeria, "hello")["reply_text"]


def test_scripted_completion_requires_answer_and_counts_repaired_errors():
    scenarios = {s["id"]: s for s in json.loads(DEFAULT_SCENARIOS.read_text())["scenarios"]}
    unresolved = run_scenario(scenarios["unanswered-question"])
    assert not unresolved["completed"]
    repaired = run_scenario(scenarios["wrong-amount-repair"])
    assert repaired["completed"] and repaired["ever_committed_wrong_amount"]
    assert repaired["final_wrong_amounts"] == 0
    assert repaired["first_completed_turn"] == 3
    target = scenarios["direct-sale"]["expected"]
    assert wrong_amount_count(target * 2, target) == 1


def test_explorer_without_audio_cannot_serve_corpus_or_product_data():
    client = TestClient(create_explorer_app(audio_enabled=False))
    assert client.get("/audio-index").json() == []
    assert client.get("/audio/sautiledger-clips/case01").status_code == 404
    assert client.get("/state").status_code == 404


def test_pidgin_is_the_default_reply_language_for_the_pidgin_pack():
    """A trader running pcm-yo-NG has already declared her language: the app
    listens in Pidgin, so it answers in Pidgin unless she chooses otherwise."""
    client = TestClient(app())
    assert client.get("/state").json()["reply_language"] == "pcm"


def test_english_does_not_use_pidgin_cloud_voice():
    client = TestClient(app())
    client.post("/language", data={"speech_pack": "pcm-yo-NG", "reply_language": "en"})
    assert client.get("/state").json()["reply_language"] == "en"
    assert client.post("/tts", data={"text": "Please repeat."}).status_code == 204


def test_void_button_clears_only_its_confirmation():
    client = TestClient(app())
    say(client, "I sell rice for 5000 naira")
    txn_id = client.get("/state").json()["entries"][0]["id"]
    result = client.post(f"/void/{txn_id}").json()
    assert result["review"] is None
    assert result["reply_text"] == "Entry removed."
    assert choose(client).status_code == 200
