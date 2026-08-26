"""Bank-readiness statement: real computed figures only, voided rows
excluded, and the honesty framing baked into the page itself."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sautiledger.api import create_app
from sautiledger.config import Settings
from sautiledger.statement import DISCLAIMER, statement_stats


def _row(ts, type_, item, amount, status="paid", quantity=None, unit=None):
    return {"ts": ts, "type": type_, "item": item, "amount": amount,
            "payment_status": status, "quantity": quantity, "unit": unit}


def test_stats_are_real_arithmetic():
    rows = [
        _row("2026-08-24T09:00:00", "sale", "rice", 5000),
        _row("2026-08-24T15:00:00", "sale", "garri", 3000),
        _row("2026-08-25T10:00:00", "sale", "beans", 2000, status="credit"),
        _row("2026-08-25T11:00:00", "expense", "transport", 1500),
    ]
    s = statement_stats(rows)
    assert s["sales_total"] == 10000
    assert s["expense_total"] == 1500
    assert s["net"] == 8500
    assert s["sales_days"] == 2      # 24th and 25th
    assert s["active_days"] == 2
    assert s["avg_daily_sales"] == 5000
    assert s["credit_open"] == 2000


def test_statement_page_shows_book_and_disclaimer():
    app = create_app(
        Settings(pack="pcm-yo-NG", db_path=":memory:", mode="offline", sahara_api_key=None)
    )
    client = TestClient(app)
    client.post("/utterance", data={"text": "sell garri egberun meta"})
    client.post("/utterance", data={"text": "i don sell 3 derica of rice five thousand five"})

    resp = client.get("/statement")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    page = resp.text
    assert "garri" in page and "rice" in page
    assert "8,500" in page          # 3000 + 5500 total sales
    assert DISCLAIMER[:40] in page  # the honesty framing is IN the artefact


def test_statement_excludes_voided_rows():
    app = create_app(
        Settings(pack="pcm-yo-NG", db_path=":memory:", mode="offline", sahara_api_key=None)
    )
    client = TestClient(app)
    client.post("/utterance", data={"text": "sell garri egberun meta"})
    client.post("/utterance", data={"text": "no"})  # rejection voids the row

    page = client.get("/statement").text
    assert "No transactions in this period" in page


def test_admin_statement_is_gated_and_session_scoped():
    app = create_app(
        Settings(pack="pcm-yo-NG", db_path=":memory:", mode="offline",
                 sahara_api_key=None, admin_token="tok")
    )
    ama, bola = TestClient(app), TestClient(app)
    ama.post("/utterance", data={"text": "sell garri egberun meta"})
    bola.post("/utterance", data={"text": "i don sell 3 derica of rice five thousand five"})
    ama_id = ama.cookies.get("sauti_device")

    assert app is not None
    assert TestClient(app).get(f"/admin/statement?session={ama_id}").status_code == 401
    page = TestClient(app).get(
        f"/admin/statement?session={ama_id}", headers={"x-admin-token": "tok"}
    ).text
    assert "garri" in page and "rice" not in page  # Ama's book only
