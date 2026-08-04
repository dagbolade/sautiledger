"""THE single guarded network wrapper (CLAUDE.md rules 1-2).

This is the ONLY module in sautiledger allowed to perform remote HTTP.
Every transmission is measured and written to egress_log BEFORE control
returns — success or failure — so the app can always prove what it
shared. tests/test_import_guard.py walks the AST of every module to
enforce this boundary.

(llm_fallback.py and chat.py hold the only other urllib imports; both
talk exclusively to 127.0.0.1 (Ollama), which never leaves the device.)
"""

from __future__ import annotations

import urllib.error
import urllib.request
import uuid
from datetime import datetime
from urllib.parse import urlsplit

from .ledger import Ledger


class EgressError(RuntimeError):
    """The transmission failed. It was still logged."""


class EgressRecorder:
    def __init__(self, ledger: Ledger, opener=None):
        self.ledger = ledger
        # injectable for tests; defaults to real urllib
        self._open = opener or self._urllib_open

    @staticmethod
    def _urllib_open(url: str, data: bytes, headers: dict, timeout: float):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()

    def post(
        self, url: str, *, purpose: str, data: bytes, headers: dict, timeout: float = 60
    ) -> tuple[int, bytes]:
        destination = urlsplit(url).netloc
        disposition = "unknown"
        try:
            status, body = self._open(url, data, headers, timeout)
            disposition = f"sent; HTTP {status}; payload discarded after response"
            return status, body
        except Exception as exc:
            disposition = f"send failed: {type(exc).__name__}"
            raise EgressError(f"transmission to {destination} failed: {exc}") from exc
        finally:
            self.ledger.conn.execute(
                """INSERT INTO egress_log (ts, destination, purpose, bytes_sent, disposition)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    destination,
                    purpose,
                    len(data),
                    disposition,
                ),
            )
            self.ledger.conn.commit()

    # ------------------------------------------------------------ reads

    def total_bytes(self) -> int:
        row = self.ledger.conn.execute(
            "SELECT COALESCE(SUM(bytes_sent), 0) AS total FROM egress_log"
        ).fetchone()
        return row["total"]

    def log(self) -> list:
        return self.ledger.conn.execute(
            "SELECT * FROM egress_log ORDER BY id DESC"
        ).fetchall()


def encode_multipart(
    fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]
) -> tuple[bytes, str]:
    """Stdlib multipart/form-data encoder (no HTTP library needed)."""
    boundary = f"sautiledger{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for name, value in fields.items():
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            str(value).encode("utf-8"),
        ]
    for name, (filename, blob, content_type) in files.items():
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode(),
            f"Content-Type: {content_type}".encode(),
            b"",
            blob,
        ]
    lines += [f"--{boundary}--".encode(), b""]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"
