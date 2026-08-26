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


# --------------------------------------------------- multi-device sessions


def _shared_app():
    return create_app(
        Settings(pack="pcm-yo-NG", db_path=":memory:", mode="offline", sahara_api_key=None)
    )


def test_first_response_sets_a_stable_device_cookie():
    client = TestClient(_shared_app())
    first = client.post("/utterance", data={"text": "sell garri egberun meta"})
    device = first.cookies.get("sauti_device")
    assert device and len(device) == 16
    client.get("/state")
    assert client.cookies.get("sauti_device") == device  # not re-minted


def test_two_devices_interleaved_stay_isolated():
    """The one that matters: two visitors mid-conversation at once. Pending
    clarifies, confirmations, and rejections must each land in the right
    book — including a rejection that voids ONLY that visitor's row."""
    app = _shared_app()
    ama, bola = TestClient(app), TestClient(app)

    # Ama starts a sale that needs an amount; her question is now pending
    r = ama.post("/utterance", data={"text": "i don sell 3 crayfish"})
    assert "How much" in r.json()["reply_text"]

    # Bola logs a complete sale while Ama's clarify is open
    r = bola.post("/utterance", data={"text": "sell garri egberun meta"})
    assert "three thousand naira" in r.json()["reply_text"]

    # Ama answers HER pending question — it must not touch Bola's turn state
    r = ama.post("/utterance", data={"text": "egberun meji"})
    assert "crayfish" in r.json()["reply_text"]
    assert "two thousand naira" in r.json()["reply_text"]

    # Bola rejects HER readback — voids the garri, never the crayfish
    r = bola.post("/utterance", data={"text": "no"})
    assert "remove" in r.json()["reply_text"]

    ama_state = ama.get("/state").json()
    bola_state = bola.get("/state").json()
    assert ama_state["sales_total"] == 2000
    assert [e["item"] for e in ama_state["entries"]] == ["crayfish"]
    assert ama_state["entries"][0]["payment_status"] == "paid"
    assert bola_state["sales_total"] == 0
    assert [e["payment_status"] for e in bola_state["entries"]] == ["voided"]


def test_void_cannot_cross_devices():
    app = _shared_app()
    ama, bola = TestClient(app), TestClient(app)
    ama.post("/utterance", data={"text": "sell garri egberun meta"})
    txn_id = ama.get("/state").json()["entries"][0]["id"]

    assert bola.post(f"/void/{txn_id}").status_code == 404
    assert ama.get("/state").json()["entries"][0]["payment_status"] == "paid"
    assert ama.post(f"/void/{txn_id}").status_code == 200  # owner still can


def test_presession_database_migrates_with_rows_tagged_default(tmp_path):
    """A ledger written before the session era gains the session_id column
    on open; its rows stay visible under 'default' and invisible to any
    device session."""
    import sqlite3

    db = str(tmp_path / "old.db")
    conn = sqlite3.connect(db)
    conn.executescript(
        """CREATE TABLE transactions (
               id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
               type TEXT NOT NULL, item TEXT, quantity INTEGER, unit TEXT,
               amount INTEGER, amount_each INTEGER, currency TEXT NOT NULL,
               payment_status TEXT NOT NULL DEFAULT 'paid', due TEXT,
               raw_utterance TEXT);
           CREATE TABLE egress_log (
               id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
               destination TEXT NOT NULL, purpose TEXT NOT NULL,
               bytes_sent INTEGER NOT NULL, disposition TEXT NOT NULL);"""
    )
    from datetime import datetime
    conn.execute(
        "INSERT INTO transactions (ts, type, item, amount, currency) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), "sale", "rice", 5500, "NGN"),
    )
    conn.commit()
    conn.close()

    from sautiledger.ledger import Ledger

    ledger = Ledger(db)  # opens as the 'default' session
    n, total = ledger.sales_total("today")
    assert (n, total) == (1, 5500)
    assert ledger.scoped("abcdef0123456789").sales_total("today") == (0, 0)
