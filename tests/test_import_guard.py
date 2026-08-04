"""AST guard for CLAUDE.md rules 1-2: egress.py is the only module that
may perform remote HTTP. This turns the privacy claim into an enforced
property of the codebase."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "sautiledger"

# No third-party HTTP client anywhere — egress.py itself uses urllib.
BANNED_EVERYWHERE = {"requests", "httpx", "aiohttp", "urllib3", "websockets"}

# Stdlib network modules: only in the egress wrapper and the two modules
# that talk exclusively to localhost Ollama (never egress).
NETWORK_MODULES = {"urllib", "http", "socket", "ftplib", "smtplib"}
NETWORK_ALLOWLIST = {"egress.py", "llm_fallback.py"}


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_no_http_client_outside_egress():
    for path in SRC.glob("*.py"):
        roots = _imported_roots(path)
        banned = roots & BANNED_EVERYWHERE
        assert not banned, f"{path.name} imports {banned} — all HTTP goes through egress.py"
        if path.name not in NETWORK_ALLOWLIST:
            network = roots & NETWORK_MODULES
            assert not network, (
                f"{path.name} imports {network} — only egress.py (remote) and "
                f"llm_fallback.py (localhost Ollama) may touch the network"
            )
