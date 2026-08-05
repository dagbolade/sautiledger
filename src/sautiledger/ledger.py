"""SQLite ledger — plain SQL, stdlib sqlite3, no ORM.

The egress_log table is created here too (CLAUDE.md rule 2); it is
written by egress.py from phase 3 onward.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import ParseResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT NOT NULL,
    type           TEXT NOT NULL,
    item           TEXT,
    quantity       INTEGER,
    unit           TEXT,
    amount         INTEGER,
    amount_each    INTEGER,
    currency       TEXT NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'paid',
    due            TEXT,
    raw_utterance  TEXT
);
CREATE TABLE IF NOT EXISTS egress_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    destination TEXT NOT NULL,
    purpose     TEXT NOT NULL,
    bytes_sent  INTEGER NOT NULL,
    disposition TEXT NOT NULL
);
"""

_CORRECTABLE_FIELDS = {"amount", "amount_each", "item", "quantity", "unit", "payment_status"}


class Ledger:
    def __init__(self, path: str = "data/ledger.db"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: FastAPI serves requests from a threadpool;
        # sqlite3 serialises access internally at this scale.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ------------------------------------------------------------ writes

    def add_transaction(self, parse: ParseResult, raw_utterance: str) -> int:
        cur = self.conn.execute(
            """INSERT INTO transactions
               (ts, type, item, quantity, unit, amount, amount_each, currency, raw_utterance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(timespec="seconds"),
                parse.type or "sale",
                parse.item,
                parse.quantity,
                parse.unit,
                parse.amount,
                parse.amount_each,
                parse.currency,
                raw_utterance,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def correct_last(self, field: str, value, due: str | None = None) -> sqlite3.Row | None:
        if field not in _CORRECTABLE_FIELDS:
            raise ValueError(f"not a correctable field: {field}")
        last = self.last_transaction()
        if last is None:
            return None
        self.conn.execute(
            f"UPDATE transactions SET {field} = ?, due = COALESCE(?, due) WHERE id = ?",
            (value, due, last["id"]),
        )
        self.conn.commit()
        return self.last_transaction()

    # ------------------------------------------------------------ reads

    def void_transaction(self, txn_id: int) -> sqlite3.Row | None:
        """Soft delete: the row stays in the DB marked 'voided' (auditable,
        never silent) and drops out of every total and the UI list."""
        row = self.conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (txn_id,)
        ).fetchone()
        if row is None:
            return None
        self.conn.execute(
            "UPDATE transactions SET payment_status = 'voided' WHERE id = ?", (txn_id,)
        )
        self.conn.commit()
        print(f"voided txn #{txn_id}: {row['item']} {row['amount']}", flush=True)
        return row

    def last_transaction(self) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM transactions WHERE payment_status != 'voided' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()

    def _since(self, period: str) -> str:
        today = date.today()
        if period == "this_week":
            return (today - timedelta(days=today.weekday())).isoformat()
        if period == "yesterday":
            return (today - timedelta(days=1)).isoformat()
        return today.isoformat()  # default: today

    def sales_total(self, period: str) -> tuple[int, int]:
        row = self.conn.execute(
            """SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
               FROM transactions WHERE type = 'sale' AND payment_status != 'voided' AND ts >= ?""",
            (self._since(period),),
        ).fetchone()
        return row["n"], row["total"]

    def expenses_total(self, period: str) -> tuple[int, int]:
        row = self.conn.execute(
            """SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
               FROM transactions WHERE type = 'expense' AND payment_status != 'voided' AND ts >= ?""",
            (self._since(period),),
        ).fetchone()
        return row["n"], row["total"]

    def item_total(self, item: str, period: str) -> tuple[int, int]:
        row = self.conn.execute(
            """SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
               FROM transactions WHERE type = 'sale' AND payment_status != 'voided' AND item = ? AND ts >= ?""",
            (item, self._since(period)),
        ).fetchone()
        return row["n"], row["total"]

    def top_item(self, period: str) -> tuple[str, int] | None:
        row = self.conn.execute(
            """SELECT item, COALESCE(SUM(amount), 0) AS total
               FROM transactions
               WHERE type = 'sale' AND payment_status != 'voided' AND item IS NOT NULL AND ts >= ?
               GROUP BY item ORDER BY total DESC LIMIT 1""",
            (self._since(period),),
        ).fetchone()
        return (row["item"], row["total"]) if row else None

    def credit_outstanding(self) -> int:
        row = self.conn.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total
               FROM transactions WHERE payment_status = 'credit'"""
        ).fetchone()
        return row["total"]

    def entries(self, period: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM transactions WHERE ts >= ? ORDER BY id",
            (self._since(period),),
        ).fetchall()
