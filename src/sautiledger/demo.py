"""One-command demo: fresh empty ledger + server with demo config.

Run: python -m sautiledger.demo   (= make demo)
Then open http://127.0.0.1:8090 on the phone/laptop.

Mode comes from .env: with SAHARA_API_KEY set it starts in CLOUD ASR;
set SAUTI_MODE=offline (or kill the wifi) for the sovereignty moment.
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn


def main() -> None:
    demo_db = Path("data/demo-ledger.db")
    if demo_db.exists():
        demo_db.unlink()  # every demo starts with an empty ledger
    os.environ["SAUTI_DB"] = str(demo_db)
    os.environ.setdefault("SAUTI_PACK", "pcm-yo-NG")

    from .api import create_app  # import after env is set

    print("SautiLedger demo -> http://127.0.0.1:8090")
    uvicorn.run(create_app(), host="127.0.0.1", port=8090, log_level="warning")


if __name__ == "__main__":
    main()
