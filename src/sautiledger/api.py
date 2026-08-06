"""FastAPI app: POST /utterance (audio or text), GET /state, static UI.

Run: python -m uvicorn sautiledger.api:app --port 8090
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agent import Agent
from .asr import FakeAsr, NotConfigured, SaharaAsyncAsr, SaharaCloudAsr
from .audio import AudioUnusable, to_wav16k
from .config import Settings, get_settings
from .egress import EgressError, EgressRecorder
from .ledger import Ledger
from .llm_fallback import ollama_if_available
from .packs import load_pack

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    pack = load_pack(settings.pack)
    ledger = Ledger(settings.db_path)
    recorder = EgressRecorder(ledger)
    agent = Agent(pack, ledger, ollama_if_available())

    if settings.mode == "cloud":
        if settings.asr_path == "async":
            asr = SaharaAsyncAsr(recorder, settings.sahara_api_key)
        else:
            asr = SaharaCloudAsr(recorder, settings.sahara_api_key)
    else:
        # Offline: FakeAsr stands in until the on-device engine lands —
        # nothing touches the network in this mode.
        asr = FakeAsr()

    app = FastAPI(title="SautiLedger")
    app.state.settings = settings
    app.state.agent = agent
    app.state.ledger = ledger
    app.state.recorder = recorder
    app.state.asr = asr

    @app.post("/utterance")
    async def utterance(
        text: str | None = Form(None),
        audio: UploadFile | None = File(None),
    ):
        egress_before = recorder.total_bytes()

        def friendly(reply: str, error: str) -> dict:
            # spoken-style bubble instead of a raw error (the UI reads this aloud)
            return {
                "transcript": "",
                "reply_text": reply,
                "parse": None,
                "error": error,
                "egress_delta": recorder.total_bytes() - egress_before,
                "egress_total": recorder.total_bytes(),
            }

        transcript_text = (text or "").strip()
        if audio is not None:
            blob = await audio.read()
            content_type = audio.content_type or "unknown"
            if settings.mode == "cloud":
                try:
                    blob, duration = to_wav16k(blob)
                except AudioUnusable as exc:
                    print(f"audio rejected: {exc}; content_type={content_type} "
                          f"bytes={len(blob)}", flush=True)
                    return friendly("I no hear you well, abeg try again.", str(exc))
            try:
                transcript_text = asr.transcribe(blob, language_hint=pack.name).text
            except EgressError as exc:
                print(f"ASR send failed: {exc}; content_type={content_type} "
                      f"bytes={len(blob)}", flush=True)
                return friendly(
                    "Network wahala — I no fit reach the cloud right now. Try again small time.",
                    str(exc),
                )
            if not transcript_text:
                return friendly("I no hear you well, abeg talk am again.", "empty transcript")
        if not transcript_text:
            return JSONResponse(status_code=400, content={"error": "no text or audio provided"})

        reply = agent.handle(transcript_text)
        return {
            "transcript": transcript_text,
            "reply_text": reply,
            "parse": (agent.pending.to_dict() if agent.pending else None),
            "egress_delta": recorder.total_bytes() - egress_before,
            "egress_total": recorder.total_bytes(),
        }

    @app.post("/void/{txn_id}")
    def void(txn_id: int):
        row = ledger.void_transaction(txn_id)
        if row is None:
            return JSONResponse(status_code=404, content={"error": "no such entry"})
        return {"ok": True, "voided": txn_id}

    @app.get("/state")
    def state():
        entries = [dict(row) for row in ledger.entries("today")]
        sales_n, sales_total = ledger.sales_total("today")
        return {
            "mode": settings.mode,
            "pack": pack.name,
            "currency": pack.currency,
            "entries": entries,
            "sales_count": sales_n,
            "sales_total": sales_total,
            "egress_total": recorder.total_bytes(),
            "egress_log": [dict(row) for row in recorder.log()],
        }

    if STATIC_DIR.exists():
        @app.get("/")
        def index():
            return FileResponse(STATIC_DIR / "index.html")

        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()
