import hashlib
import re

from fastapi.testclient import TestClient

from sautiledger.agent import Agent
from sautiledger.api import create_app, STATIC_DIR
from sautiledger.config import Settings
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack


def agent():
    return Agent(load_pack("pcm-yo-NG"), Ledger(":memory:"))


def test_customer_suffix_does_not_hide_the_spoken_amount():
    book = agent()
    text = "i sell biscuits 220 naira for iya chinonso"
    assert "Correct?" in book.handle(text)
    row = book.ledger.last_transaction()
    assert (row["item"], row["amount"], row["quantity"]) == ("biscuits", 220, None)
    assert row["raw_utterance"] == text
    book.handle("yes")
    assert not book.awaiting_confirm


def test_customer_suffix_with_a_second_number_is_not_discarded():
    book = agent()
    book.handle("i sell biscuits 220 naira for iya chinonso 500")
    assert not book.ledger.all_transactions()


def test_yoruba_confirmations_and_unknown_reply_keep_safety_loop():
    for confirmation in ("beeni", "bee ni"):
        book = agent()
        book.handle("oya na mo ta crate eyin meji fun 6000")
        book.handle(confirmation)
        assert not book.awaiting_confirm and book.pending is None
        assert book.ledger.sales_total("today")[1] == 6000
    book = agent()
    book.handle("i sell 3 biscuits for 500 naira")
    assert "Correct?" in book.handle("something I cannot understand")
    assert book.awaiting_confirm
    book.handle("no")
    assert book.ledger.sales_total("today")[1] == 0


def test_sales_question_is_gross_sales_and_yoruba_book_question_reads_entries():
    book = agent()
    for text in ("i sell 3 biscuits for 500 naira", "oya na mo ta isu meji fun 6000", "oya na mo ta crate eyin meji fun 6000"):
        book.handle(text)
        book.handle("beeni")
    book.handle("i buy fuel for 1000 naira")
    book.handle("yes")
    answer = book.handle("what are my sales today")
    assert "twelve thousand five hundred naira" in answer
    assert "3 sales" in answer
    recap = book.handle("kini gbogbo oja mi leni")
    assert all(item in recap for item in ("biscuits", "isu", "eyin"))
    assert len(book.ledger.all_transactions()) == 4


def test_index_versions_assets_and_prevents_stale_html():
    client = TestClient(create_app(Settings(pack="pcm-yo-NG", db_path=":memory:", mode="offline", sahara_api_key=None, agent="none")))
    response = client.get("/")
    assert response.headers["cache-control"] == "no-store"
    for asset in ("app.js", "app.css"):
        digest = hashlib.sha256((STATIC_DIR / asset).read_bytes()).hexdigest()[:16]
        url = f"/static/{asset}?v={digest}"
        assert url in response.text
        assert client.get(url).content == (STATIC_DIR / asset).read_bytes()
