"""SQLite ledger — plain SQL, stdlib sqlite3, no ORM.

Every row belongs to a session (one visitor's book). A Ledger object is a
session-scoped view: it shares one connection with its siblings but every
read and write is filtered to its own session_id, so one trader's book can
never leak into another's. Rows from before the multi-session era carry
session_id 'default'.

The egress_log table is created here too; egress.py writes to it.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import ParseResult

DEFAULT_SESSION = "default"

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
    raw_utterance  TEXT,
    session_id     TEXT NOT NULL DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS egress_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    destination TEXT NOT NULL,
    purpose     TEXT NOT NULL,
    bytes_sent  INTEGER NOT NULL,
    disposition TEXT NOT NULL,
    session_id  TEXT NOT NULL DEFAULT 'default'
);
CREATE INDEX IF NOT EXISTS idx_txn_session ON transactions(session_id);
CREATE INDEX IF NOT EXISTS idx_egress_session ON egress_log(session_id);
CREATE TABLE IF NOT EXISTS usage_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    input_mode  TEXT NOT NULL,
    transcript  TEXT,
    reply       TEXT,
    outcome     TEXT NOT NULL,
    audio_file  TEXT
);
CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_log(session_id);
CREATE TABLE IF NOT EXISTS session_prefs (
    session_id   TEXT PRIMARY KEY,
    retain_audio INTEGER NOT NULL DEFAULT 0,
    updated      TEXT NOT NULL
);
"""

_CORRECTABLE_FIELDS = {"amount", "amount_each", "item", "quantity", "unit", "payment_status"}


def _migrate(conn: sqlite3.Connection) -> None:
    """Pre-session databases lack the session_id columns; add them in place.
    Existing rows keep the 'default' tag so nothing already written moves."""
    for table in ("transactions", "egress_log"):
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if cols and "session_id" not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'"
            )


class Ledger:
    def __init__(self, path: str = "data/ledger.db", session_id: str = DEFAULT_SESSION):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: FastAPI serves requests from a threadpool;
        # sqlite3 serialises access internally at this scale.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        _migrate(self.conn)
        self.conn.executescript(SCHEMA)
        self.session_id = session_id

    def scoped(self, session_id: str) -> "Ledger":
        """A sibling view over the same database, filtered to another session."""
        twin = object.__new__(Ledger)
        twin.conn = self.conn
        twin.session_id = session_id
        return twin

    # ------------------------------------------------------------ writes

    def add_transaction(self, parse: ParseResult, raw_utterance: str) -> int:
        cur = self.conn.execute(
            """INSERT INTO transactions
               (ts, type, item, quantity, unit, amount, amount_each, currency,
                raw_utterance, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                self.session_id,
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

    def void_transaction(self, txn_id: int) -> sqlite3.Row | None:
        """Soft delete: the row stays in the DB marked 'voided' (auditable,
        never silent) and drops out of every total and the UI list. Only
        rows in this session's book are reachable — no cross-book voiding."""
        row = self.conn.execute(
            "SELECT * FROM transactions WHERE id = ? AND session_id = ?",
            (txn_id, self.session_id),
        ).fetchone()
        if row is None:
            return None
        self.conn.execute(
            "UPDATE transactions SET payment_status = 'voided' WHERE id = ?", (txn_id,)
        )
        self.conn.commit()
        print(f"voided txn #{txn_id}: {row['item']} {row['amount']}", flush=True)
        return row

    # -------------------------------------------------- field-test observability
    # (usage_log is local to the database like everything else — it is
    #  never transmitted; the admin export reads it out with consent)

    def record_usage(self, input_mode: str, transcript: str | None,
                     reply: str | None, outcome: str,
                     audio_file: str | None = None) -> None:
        self.conn.execute(
            """INSERT INTO usage_log
               (ts, session_id, input_mode, transcript, reply, outcome, audio_file)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(timespec="seconds"), self.session_id,
             input_mode, transcript, reply, outcome, audio_file),
        )
        self.conn.commit()

    def usage_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM usage_log WHERE session_id = ? ORDER BY id",
            (self.session_id,),
        ).fetchall()

    @property
    def retain_audio(self) -> bool:
        row = self.conn.execute(
            "SELECT retain_audio FROM session_prefs WHERE session_id = ?",
            (self.session_id,),
        ).fetchone()
        return bool(row and row["retain_audio"])

    def set_retain_audio(self, value: bool) -> None:
        self.conn.execute(
            """INSERT INTO session_prefs (session_id, retain_audio, updated)
               VALUES (?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET retain_audio = ?, updated = ?""",
            (self.session_id, int(value),
             datetime.now().isoformat(timespec="seconds"),
             int(value), datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def max_txn_id(self) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) AS m FROM transactions WHERE session_id = ?",
            (self.session_id,),
        ).fetchone()
        return row["m"]

    def voided_count(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM transactions "
            "WHERE session_id = ? AND payment_status = 'voided'",
            (self.session_id,),
        ).fetchone()
        return row["n"]

    def sessions_overview(self) -> list[sqlite3.Row]:
        """One row per session across the whole database (admin view)."""
        return self.conn.execute(
            """SELECT session_id,
                      COUNT(*) AS transactions,
                      MIN(ts) AS first_ts, MAX(ts) AS last_ts,
                      (SELECT COUNT(*) FROM usage_log u
                        WHERE u.session_id = t.session_id) AS utterances,
                      (SELECT COUNT(*) FROM usage_log u
                        WHERE u.session_id = t.session_id
                          AND u.audio_file IS NOT NULL) AS retained_clips
               FROM transactions t GROUP BY session_id ORDER BY MAX(ts) DESC"""
        ).fetchall()

    # ------------------------------------------------------------ reads

    def last_transaction(self) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM transactions WHERE payment_status != 'voided' "
            "AND session_id = ? ORDER BY id DESC LIMIT 1",
            (self.session_id,),
        ).fetchone()

    def has_logged_item(self, item: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM transactions WHERE item = ? AND session_id = ? LIMIT 1",
            (item, self.session_id),
        ).fetchone() is not None

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
               FROM transactions WHERE type = 'sale' AND payment_status != 'voided'
               AND session_id = ? AND ts >= ?""",
            (self.session_id, self._since(period)),
        ).fetchone()
        return row["n"], row["total"]

    def expenses_total(self, period: str) -> tuple[int, int]:
        row = self.conn.execute(
            """SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
               FROM transactions WHERE type = 'expense' AND payment_status != 'voided'
               AND session_id = ? AND ts >= ?""",
            (self.session_id, self._since(period)),
        ).fetchone()
        return row["n"], row["total"]

    def item_total(self, item: str, period: str) -> tuple[int, int]:
        row = self.conn.execute(
            """SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
               FROM transactions WHERE type = 'sale' AND payment_status != 'voided'
               AND item = ? AND session_id = ? AND ts >= ?""",
            (item, self.session_id, self._since(period)),
        ).fetchone()
        return row["n"], row["total"]

    def top_item(self, period: str) -> tuple[str, int] | None:
        row = self.conn.execute(
            """SELECT item, COALESCE(SUM(amount), 0) AS total
               FROM transactions
               WHERE type = 'sale' AND payment_status != 'voided' AND item IS NOT NULL
               AND session_id = ? AND ts >= ?
               GROUP BY item ORDER BY total DESC LIMIT 1""",
            (self.session_id, self._since(period)),
        ).fetchone()
        return (row["item"], row["total"]) if row else None

    def credit_outstanding(self) -> int:
        row = self.conn.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total
               FROM transactions WHERE payment_status = 'credit' AND session_id = ?""",
            (self.session_id,),
        ).fetchone()
        return row["total"]

    def all_transactions(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM transactions WHERE session_id = ? ORDER BY id",
            (self.session_id,),
        ).fetchall()

    def entries(self, period: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM transactions WHERE session_id = ? AND ts >= ? ORDER BY id",
            (self.session_id, self._since(period)),
        ).fetchall()
