"""Phone testing mode: serve the UI over HTTPS on the local network.

Why HTTPS: browsers block getUserMedia (the mic) on insecure origins —
plain http://192.168.x.x will never show the mic prompt. A self-signed
cert fixes it: the phone shows one scary warning, you tap
Advanced -> Proceed, and the mic works from then on.

Run: python -m sautiledger.phone   (= make phone)
"""

from __future__ import annotations

import shutil
import socket
import subprocess
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[2]
CERT_DIR = ROOT / "certs"
CERT = CERT_DIR / "dev-cert.pem"
KEY = CERT_DIR / "dev-key.pem"
PORT = 8443


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no packet is sent; just picks the route
        return s.getsockname()[0]
    finally:
        s.close()


def ensure_cert() -> None:
    if CERT.exists() and KEY.exists():
        return
    openssl = shutil.which("openssl") or r"C:\Program Files\Git\usr\bin\openssl.exe"
    if not Path(openssl).exists():
        raise SystemExit(
            "No dev cert and no openssl found. Generate one with:\n"
            f'  openssl req -x509 -newkey rsa:2048 -nodes -days 365 '
            f'-subj "/CN=sautiledger.local" -keyout "{KEY}" -out "{CERT}"'
        )
    CERT_DIR.mkdir(exist_ok=True)
    subprocess.run(
        [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365",
         "-subj", "/CN=sautiledger.local", "-keyout", str(KEY), "-out", str(CERT)],
        check=True, capture_output=True,
    )
    print(f"generated self-signed cert in {CERT_DIR}")


def main() -> None:
    ensure_cert()
    ip = lan_ip()
    from .api import create_app  # after env is settled

    print("=" * 56)
    print(f"  Open on your phone:  https://{ip}:{PORT}")
    print("=" * 56)
    print("- Phone and laptop must be on the SAME network.")
    print("- The browser will warn about the certificate ONCE:")
    print("  tap Advanced -> Proceed. Then the mic prompt appears.")
    print("- If Windows Firewall asks, click Allow (private networks).")
    print("- If the page never loads, the venue wifi likely isolates")
    print("  clients: use your phone's hotspot instead (laptop joins it).")
    uvicorn.run(create_app(), host="0.0.0.0", port=PORT,
                ssl_certfile=str(CERT), ssl_keyfile=str(KEY), log_level="warning")


if __name__ == "__main__":
    main()
