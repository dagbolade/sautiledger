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


# ------------------------------------------- field-test instrumentation


def _instrumented_app(tmp_path):
    return create_app(Settings(
        pack="pcm-yo-NG", db_path=":memory:", mode="offline", sahara_api_key=None,
        recordings_dir=str(tmp_path / "recordings"), admin_token="test-admin-token",
    ))


def test_every_turn_lands_in_usage_log_with_honest_outcomes(tmp_path):
    app = _instrumented_app(tmp_path)
    client = TestClient(app)
    client.post("/utterance", data={"text": "sell garri egberun meta"})     # logged
    client.post("/utterance", data={"text": "i don sell 3 crayfish"})       # clarify
    client.post("/utterance", data={"text": "egberun meji"})                # logged
    client.post("/utterance", data={"text": "how much i don make today"})   # reply
    device = client.cookies.get("sauti_device")

    resp = client.get(f"/admin/export?session={device}&what=usage",
                      headers={"x-admin-token": "test-admin-token"})
    assert resp.status_code == 200
    import csv as csv_mod
    rows = list(csv_mod.DictReader(resp.text.splitlines()))
    assert [r["outcome"] for r in rows] == ["logged", "clarify", "logged", "reply"]
    assert all(r["input_mode"] == "text" for r in rows)
    assert rows[1]["transcript"] == "i don sell 3 crayfish"


def test_audio_retention_is_off_by_default_and_honours_consent(tmp_path):
    app = _instrumented_app(tmp_path)
    client = TestClient(app)

    assert client.get("/state").json()["retain_audio"] is False
    client.post("/utterance",
                files={"audio": ("clip.webm", b"case05.wav", "audio/webm")})
    rec_root = tmp_path / "recordings"
    assert not rec_root.exists()  # nothing kept without consent

    resp = client.post("/consent", data={"retain_audio": "true"})
    assert resp.json() == {"retain_audio": True}
    assert client.get("/state").json()["retain_audio"] is True
    client.post("/utterance",
                files={"audio": ("clip.webm", b"case05.wav", "audio/webm")})
    device = client.cookies.get("sauti_device")
    clips = list((rec_root / device).iterdir())
    assert len(clips) == 1
    assert clips[0].read_bytes() == b"case05.wav"  # exactly what the model heard

    # and the clip is fetchable through the admin zip
    resp = client.get(f"/admin/audio?session={device}",
                      headers={"x-admin-token": "test-admin-token"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    client.post("/consent", data={"retain_audio": "false"})
    client.post("/utterance",
                files={"audio": ("clip.webm", b"case05.wav", "audio/webm")})
    assert len(list((rec_root / device).iterdir())) == 1  # no new clip


def test_admin_surface_is_locked(tmp_path):
    app = _instrumented_app(tmp_path)
    client = TestClient(app)
    assert client.get("/admin/sessions").status_code == 401
    assert client.get("/admin/sessions",
                      headers={"x-admin-token": "wrong"}).status_code == 401
    ok = client.get("/admin/sessions", headers={"x-admin-token": "test-admin-token"})
    assert ok.status_code == 200

    # no token configured -> the whole surface is disabled
    bare = TestClient(_shared_app())
    assert bare.get("/admin/sessions").status_code == 403


def test_admin_dashboard_gated_and_shows_fleet(tmp_path):
    app = _instrumented_app(tmp_path)
    ama, bola = TestClient(app), TestClient(app)
    ama.post("/utterance", data={"text": "sell garri egberun meta"})
    ama.post("/utterance", data={"text": "i don sell 3 crayfish"})   # clarify
    bola.post("/utterance", data={"text": "i don sell 3 derica of rice five thousand five"})

    assert ama.get("/admin/dashboard").status_code == 401
    # token in the query string works too — the dashboard is a browser page
    page = ama.get("/admin/dashboard?token=test-admin-token")
    assert page.status_code == 200
    body = page.text
    assert ama.cookies.get("sauti_device")[:8] in body
    assert bola.cookies.get("sauti_device")[:8] in body
    assert "8,500" in body        # fleet sales: 3000 + 5500
    assert "clarify" in body      # outcomes table
    assert "/admin/statement?session=" in body  # export links per session


def test_dashboard_visit_teaches_the_browser(tmp_path):
    app = _instrumented_app(tmp_path)
    admin = TestClient(app)
    assert admin.get("/admin/dashboard").status_code == 401
    assert admin.get("/admin/dashboard?token=test-admin-token").status_code == 200
    # cookie set by that visit now carries the auth on its own
    assert admin.get("/admin/dashboard").status_code == 200
    assert admin.get("/admin/sessions").status_code == 200
