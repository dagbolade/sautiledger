"""FastAPI app: POST /utterance (audio or text), GET /state, static UI.

Every visitor gets their own book. A long-lived cookie names the device;
each device id maps to a session — its own ledger view, agent turn-state,
egress meter, and ASR client — so two traders on the same URL can never
see or touch each other's records.

Run: python -m uvicorn sautiledger.api:app --port 8090
"""

from __future__ import annotations

import csv
import io
import re
import secrets
import threading
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agent import Agent
from .asr import FakeAsr, SaharaAsyncAsr, SaharaCloudAsr
from .audio import AudioUnusable, to_wav16k
from .config import Settings, get_settings
from .egress import EgressError, EgressRecorder
from .ledger import DEFAULT_SESSION, Ledger
from .llm_fallback import HostedLlmClient, ollama_if_available
from .packs import load_pack
from .statement import build_statement_html

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

DEVICE_COOKIE = "sauti_device"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
_DEVICE_ID = re.compile(r"[0-9a-f]{16}")
# in-memory sessions kept at once; oldest-idle is dropped beyond this
# (its ledger rows persist — a returning cookie just gets a fresh session)
MAX_LIVE_SESSIONS = 300
# per-device transcriptions per day: enough for a full trading day, small
# enough that a shared link cannot drain the ASR credits
ASR_DAILY_CAP = 150
_ASR_PURPOSE = "your voice clip, sent for transcription"


def _make_llm(settings: Settings, recorder: EgressRecorder):
    """Fallback-model selection. "hosted" needs an explicit opt-in AND a
    token; "auto" tries local Ollama and otherwise runs grammar-only —
    utterance text never leaves the device by default."""
    if settings.agent == "none":
        return None
    if settings.agent == "hosted":
        return HostedLlmClient(recorder, settings.hf_token) if settings.hf_token else None
    return ollama_if_available()


class _Session:
    def __init__(self, settings: Settings, pack, base_ledger: Ledger, device_id: str):
        self.ledger = base_ledger.scoped(device_id)
        self.recorder = EgressRecorder(self.ledger)
        self.agent = Agent(pack, self.ledger, _make_llm(settings, self.recorder))
        if settings.mode == "cloud":
            asr_cls = SaharaAsyncAsr if settings.asr_path == "async" else SaharaCloudAsr
            self.asr = asr_cls(self.recorder, settings.sahara_api_key)
        else:
            # Offline: FakeAsr stands in until the on-device engine lands —
            # nothing touches the network in this mode.
            self.asr = FakeAsr()
        self.touched = 0


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    pack = load_pack(settings.pack)
    base_ledger = Ledger(settings.db_path)

    # consented voice clips land next to the database (i.e. on the volume);
    # an in-memory database with no explicit dir means retention is off
    rec_dir = settings.recordings_dir
    if rec_dir is None and settings.db_path != ":memory:":
        rec_dir = str(Path(settings.db_path).parent / "recordings")

    sessions: dict[str, _Session] = {}
    lock = threading.Lock()
    clock = [0]  # monotonic touch counter for oldest-idle eviction

    def session_for(device_id: str) -> _Session:
        with lock:
            sess = sessions.get(device_id)
            if sess is None:
                if len(sessions) >= MAX_LIVE_SESSIONS:
                    oldest = min(sessions, key=lambda k: sessions[k].touched)
                    del sessions[oldest]
                sess = _Session(settings, pack, base_ledger, device_id)
                sessions[device_id] = sess
            clock[0] += 1
            sess.touched = clock[0]
            return sess

    def resolve_device(request: Request, response: Response) -> str:
        cookie = request.cookies.get(DEVICE_COOKIE, "")
        if _DEVICE_ID.fullmatch(cookie):
            return cookie
        device_id = secrets.token_hex(8)
        response.set_cookie(
            DEVICE_COOKIE, device_id,
            max_age=_COOKIE_MAX_AGE, httponly=True, samesite="lax",
        )
        return device_id

    app = FastAPI(title="SautiLedger")
    app.state.settings = settings
    app.state.ledger = base_ledger

    @app.post("/utterance")
    async def utterance(
        request: Request,
        response: Response,
        text: str | None = Form(None),
        audio: UploadFile | None = File(None),
    ):
        sess = session_for(resolve_device(request, response))
        recorder, agent, ledger = sess.recorder, sess.agent, sess.ledger
        asr = sess.asr
        egress_before = recorder.total_bytes()
        input_mode = "voice" if audio is not None else "text"
        saved_clip: str | None = None
        transcript_text = (text or "").strip()

        def friendly(reply: str, error: str, outcome: str) -> dict:
            # spoken-style bubble instead of a raw error (the UI reads this
            # aloud); every turn — failures included — lands in usage_log
            ledger.record_usage(input_mode, transcript_text or None, reply,
                                outcome, saved_clip)
            return {
                "transcript": "",
                "reply_text": reply,
                "parse": None,
                "error": error,
                "egress_delta": recorder.total_bytes() - egress_before,
                "egress_total": recorder.total_bytes(),
            }

        if audio is not None:
            blob = await audio.read()
            content_type = audio.content_type or "unknown"
            if settings.mode == "cloud":
                if recorder.sends_today(_ASR_PURPOSE) >= ASR_DAILY_CAP:
                    return friendly(
                        "Voice don reach im limit for today o. Type am instead, abeg.",
                        "daily ASR cap reached", "capped",
                    )
                try:
                    blob, duration = to_wav16k(blob)
                except AudioUnusable as exc:
                    print(f"audio rejected: {exc}; content_type={content_type} "
                          f"bytes={len(blob)}", flush=True)
                    return friendly("I no hear you well, abeg try again.",
                                    str(exc), "audio_unusable")
            if rec_dir and ledger.retain_audio:
                # consented retention: keep exactly the bytes the model hears
                clip_dir = Path(rec_dir) / ledger.session_id
                clip_dir.mkdir(parents=True, exist_ok=True)
                ext = ".wav" if settings.mode == "cloud" else ".bin"
                name = datetime.now().strftime("%Y%m%dT%H%M%S-%f") + ext
                (clip_dir / name).write_bytes(blob)
                saved_clip = f"{ledger.session_id}/{name}"
            try:
                transcript_text = asr.transcribe(blob, language_hint=pack.name).text
            except EgressError as exc:
                print(f"ASR send failed: {exc}; content_type={content_type} "
                      f"bytes={len(blob)}", flush=True)
                return friendly(
                    "Network wahala — I no fit reach the cloud right now. Try again small time.",
                    str(exc), "asr_failed",
                )
            if not transcript_text:
                return friendly("I no hear you well, abeg talk am again.",
                                "empty transcript", "asr_empty")
        if not transcript_text:
            return JSONResponse(status_code=400, content={"error": "no text or audio provided"})

        txn_before = ledger.max_txn_id()
        voided_before = ledger.voided_count()
        reply = agent.handle(transcript_text)
        if ledger.max_txn_id() > txn_before:
            outcome = "logged"
        elif ledger.voided_count() > voided_before:
            outcome = "voided"
        elif agent.pending is not None:
            outcome = "clarify"
        else:
            outcome = "reply"
        ledger.record_usage(input_mode, transcript_text, reply, outcome, saved_clip)
        return {
            "transcript": transcript_text,
            "reply_text": reply,
            "parse": (agent.pending.to_dict() if agent.pending else None),
            "egress_delta": recorder.total_bytes() - egress_before,
            "egress_total": recorder.total_bytes(),
        }

    @app.post("/void/{txn_id}")
    def void(txn_id: int, request: Request, response: Response):
        sess = session_for(resolve_device(request, response))
        # the scoped ledger only reaches this session's rows — a guessed id
        # from another book 404s rather than voiding someone else's sale
        row = sess.ledger.void_transaction(txn_id)
        if row is None:
            return JSONResponse(status_code=404, content={"error": "no such entry"})
        return {"ok": True, "voided": txn_id}

    @app.post("/consent")
    def consent(request: Request, response: Response, retain_audio: str = Form(...)):
        """The voice-clip retention switch. Off by default; the visitor flips
        it knowingly from the UI, and can flip it back any time (already
        saved clips stay until the admin removes them — the toggle governs
        new clips only)."""
        sess = session_for(resolve_device(request, response))
        value = retain_audio.strip().lower() in ("1", "true", "yes", "on")
        sess.ledger.set_retain_audio(value)
        return {"retain_audio": value}

    @app.get("/state")
    def state(request: Request, response: Response):
        sess = session_for(resolve_device(request, response))
        entries = [dict(row) for row in sess.ledger.entries("today")]
        sales_n, sales_total = sess.ledger.sales_total("today")
        return {
            "mode": settings.mode,
            "pack": pack.name,
            "currency": pack.currency,
            "entries": entries,
            "sales_count": sales_n,
            "sales_total": sales_total,
            "retain_audio": sess.ledger.retain_audio,
            "egress_total": sess.recorder.total_bytes(),
            "egress_log": [dict(row) for row in sess.recorder.log()],
        }

    # -------------------------------------------------- bank-readiness statement

    def _statement_response(ledger: Ledger, period: str) -> Response:
        days = 30 if period == "month" else 7
        since = (date.today() - timedelta(days=days - 1)).isoformat()
        label = f"Last {days} days · {since} to {date.today().isoformat()}"
        # a short bank-style reference, never the raw session id — a
        # non-technical reader should not meet a UUID fragment here
        owner = f"Statement ref {ledger.session_id[:4].upper()}"
        page = build_statement_html(
            ledger.statement_rows(since), pack.currency, label, days, owner
        )
        return Response(content=page, media_type="text/html")

    @app.get("/statement")
    def statement(request: Request, response: Response, period: str = "week"):
        """The visitor's own book as a lender-legible page; the browser's
        print-to-PDF turns it into the document."""
        sess = session_for(resolve_device(request, response))
        return _statement_response(sess.ledger, period)

    # -------------------------------------------------- admin (field test)
    # Token-gated export of one session's usage evidence — pulled with the
    # participant's permission. No token configured = no admin surface.

    def _admin_denied(request: Request):
        if not settings.admin_token:
            return JSONResponse(status_code=403, content={"error": "admin disabled"})
        if request.headers.get("x-admin-token") != settings.admin_token:
            return JSONResponse(status_code=401, content={"error": "bad token"})
        return None

    @app.get("/admin/sessions")
    def admin_sessions(request: Request):
        denied = _admin_denied(request)
        if denied:
            return denied
        return {"sessions": [dict(r) for r in base_ledger.sessions_overview()]}

    @app.get("/admin/export")
    def admin_export(request: Request, session: str, what: str = "usage"):
        denied = _admin_denied(request)
        if denied:
            return denied
        scoped = base_ledger.scoped(session)
        rows = scoped.usage_rows() if what == "usage" else scoped.all_transactions()
        buf = io.StringIO()
        writer = csv.writer(buf)
        if rows:
            writer.writerow(rows[0].keys())
            writer.writerows([list(r) for r in rows])
        return Response(
            content=buf.getvalue(), media_type="text/csv",
            headers={"Content-Disposition":
                     f'attachment; filename="{session}-{what}.csv"'},
        )

    @app.get("/admin/statement")
    def admin_statement(request: Request, session: str, period: str = "week"):
        denied = _admin_denied(request)
        if denied:
            return denied
        return _statement_response(base_ledger.scoped(session), period)

    @app.get("/admin/audio")
    def admin_audio(request: Request, session: str):
        denied = _admin_denied(request)
        if denied:
            return denied
        clip_dir = Path(rec_dir) / session if rec_dir else None
        if clip_dir is None or not clip_dir.exists():
            return JSONResponse(status_code=404, content={"error": "no retained clips"})
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w") as bundle:
            for clip in sorted(clip_dir.iterdir()):
                bundle.write(clip, clip.name)
        return Response(
            content=mem.getvalue(), media_type="application/zip",
            headers={"Content-Disposition":
                     f'attachment; filename="{session}-clips.zip"'},
        )

    if STATIC_DIR.exists():
        @app.get("/")
        def index():
            return FileResponse(STATIC_DIR / "index.html")

        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()
