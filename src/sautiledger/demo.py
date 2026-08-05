"""One-command demo: fresh empty ledger + server with demo config.

Run: python -m sautiledger.demo   (= make demo)
Then open http://127.0.0.1:8090 on the phone/laptop.

Mode comes from .env: with SAHARA_API_KEY set it starts in CLOUD ASR;
set SAUTI_MODE=offline (or kill the wifi) for the sovereignty moment.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def _seed_demo_rows(db_path: str) -> None:
    from .ledger import Ledger
    from .models import ParseResult

    ledger = Ledger(db_path)
    ledger.add_transaction(
        ParseResult(intent="log_transaction", type="sale", item="rice",
                    quantity=3, unit="derica", amount=5500, currency="NGN"),
        "[demo seed]",
    )
    ledger.add_transaction(
        ParseResult(intent="log_transaction", type="sale", item="garri",
                    amount=3000, currency="NGN"),
        "[demo seed]",
    )
    print("seeded 2 demo rows (raw_utterance='[demo seed]', voidable on camera)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-demo", action="store_true",
                        help="pre-load two plausible rows for B-roll shots")
    args = parser.parse_args()

    demo_db = Path("data/demo-ledger.db")
    if demo_db.exists():
        demo_db.unlink()  # every demo starts with an empty ledger
    os.environ["SAUTI_DB"] = str(demo_db)
    os.environ.setdefault("SAUTI_PACK", "pcm-yo-NG")
    if args.seed_demo:
        _seed_demo_rows(str(demo_db))

    from .api import create_app  # import after env is set

    print("SautiLedger demo -> http://127.0.0.1:8090")
    uvicorn.run(create_app(), host="127.0.0.1", port=8090, log_level="warning")


if __name__ == "__main__":
    main()
