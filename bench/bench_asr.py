"""Models under test, behind one BenchAsrClient interface.

Cloud models (Sahara, frontier) route through the app's EgressRecorder
into a bench-local DB — the egress-logging rule applies to the benchmark too.
Local whisper models are imported lazily from bench/requirements.txt
installs (NEVER added to the app's dependencies).
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Protocol

from sautiledger.asr import SaharaCloudAsr
from sautiledger.egress import EgressRecorder, encode_multipart
from sautiledger.ledger import Ledger

BENCH_DIR = Path(__file__).resolve().parent


class BenchAsrClient(Protocol):
    name: str

    def transcribe_file(self, path: Path, language_hint: str | None) -> str: ...


def bench_recorder() -> EgressRecorder:
    """All bench cloud traffic is logged here, same as the app's."""
    return EgressRecorder(Ledger(str(BENCH_DIR / "results" / "bench_egress.db")))


class SaharaBench:
    # v2.5 confirmed as the live backend 2 Sep — new name = new cache dir,
    # so v2-era transcripts are never mistaken for v2.5 output
    name = "sahara-v2.5"

    def __init__(self, recorder: EgressRecorder | None = None):
        key = os.environ.get("SAHARA_API_KEY")
        self.client = SaharaCloudAsr(recorder or bench_recorder(), key)

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        return self.client.transcribe(path.read_bytes(), language_hint=language_hint).text


class WhisperLocalBench:
    """faster-whisper, fully local. model_size: 'large-v3' or 'small'."""

    def __init__(self, model_size: str = "large-v3"):
        self.name = f"whisper-{model_size}"
        from faster_whisper import WhisperModel  # bench/requirements.txt only

        self.model = WhisperModel(model_size, compute_type="int8")

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        segments, _info = self.model.transcribe(str(path), language="en")
        return " ".join(s.text.strip() for s in segments).strip()


class OpenAiBench:
    name = "gpt-4o-transcribe"

    def __init__(self, recorder: EgressRecorder | None = None):
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.recorder = recorder or bench_recorder()

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        body, content_type = encode_multipart(
            fields={"model": "gpt-4o-transcribe"},
            files={"file": (path.name, path.read_bytes(), "audio/wav")},
        )
        _status, resp = self.recorder.post(
            "https://api.openai.com/v1/audio/transcriptions",
            purpose=f"benchmark: frontier ASR of {path.name}",
            data=body,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": content_type},
        )
        return json.loads(resp).get("text", "").strip()


class GeminiBench:
    name = "gemini-flash"

    def __init__(self, recorder: EgressRecorder | None = None):
        self.key = os.environ.get("GEMINI_API_KEY")
        if not self.key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self.recorder = recorder or bench_recorder()

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        payload = json.dumps({
            "contents": [{"parts": [
                {"text": "Transcribe this audio verbatim. Return only the transcript."},
                {"inline_data": {
                    "mime_type": "audio/wav",
                    "data": base64.b64encode(path.read_bytes()).decode(),
                }},
            ]}]
        }).encode()
        # Intron's own multimodal bench lists Gemini-3-Flash; override with
        # GEMINI_ASR_MODEL if the id differs when the key arrives
        model = os.environ.get("GEMINI_ASR_MODEL", "gemini-3-flash")
        _status, resp = self.recorder.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.key}",
            purpose=f"benchmark: frontier ASR of {path.name}",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        data = json.loads(resp)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


class SaharaRawBench:
    """Sahara with LLM post-corrections DISABLED (use_disable_llm_corrections
    defaults to FALSE on the API, i.e. an LLM rewrites transcripts unless
    told not to — docs read 3 Sep). This row isolates the acoustic model
    from the post-processor; 'sahara-v2.5' remains the as-deployed row."""

    name = "sahara-v2.5-raw"

    def __init__(self, recorder: EgressRecorder | None = None):
        self.key = os.environ.get("SAHARA_API_KEY")
        if not self.key:
            raise RuntimeError("SAHARA_API_KEY not set")
        self.recorder = recorder or bench_recorder()

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        from sautiledger.asr import LANGUAGE_CODES, SAHARA_SYNC_URL

        language = LANGUAGE_CODES.get(language_hint or "", "en")
        body, content_type = encode_multipart(
            fields={
                "audio_file_name": path.name,
                "use_language_asr_input": language,
                "use_disable_llm_corrections": "TRUE",
            },
            files={"audio_file_blob": (path.name, path.read_bytes(), "audio/wav")},
        )
        _status, resp = self.recorder.post(
            SAHARA_SYNC_URL,
            purpose=f"benchmark: raw (uncorrected) Sahara ASR of {path.name}",
            data=body,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": content_type},
        )
        return ((json.loads(resp).get("data") or {}).get("audio_transcript") or "").strip()


class OmnilingualBench:
    """facebook omnilingual-ASR via a persistent WSL worker (fairseq2 ships
    no Windows wheels; venv ~/omni in Ubuntu-24.04, libsndfile shimmed from
    the soundfile wheel). The model loads ONCE per run; clips stream over
    stdin/stdout as JSON lines. Fully local — zero egress, zero credits."""

    OMNI_LANGS = {
        "pcm-yo-NG": "pcm_Latn",
        "sw-KE": "swh_Latn",
        "ha-NG": "hau_Latn",
        "sh-ZW": "sna_Latn",
    }

    def __init__(self, model_card: str = "omniASR_CTC_300M", distro: str = "Ubuntu-24.04"):
        self.name = "omnilingual-" + model_card.replace("omniASR_", "").replace("_", "-").lower()
        import subprocess

        worker = _to_wsl_path(BENCH_DIR / "omni_worker.py")
        self.proc = subprocess.Popen(
            ["wsl", "-d", distro, "--", "bash", "-c",
             f"cd ~ && LD_LIBRARY_PATH=~/omni/shimlib ./omni/bin/python {worker} {model_card}"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
        )
        ready = json.loads(self.proc.stdout.readline() or "{}")
        if not ready.get("ready"):
            raise RuntimeError(f"omni worker failed to start: {ready}")

    def transcribe_file(self, path: Path, language_hint: str | None) -> str:
        req = {"path": _to_wsl_path(path),
               "lang": self.OMNI_LANGS.get(language_hint or "", "eng_Latn")}
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("omni worker died mid-run")
        out = json.loads(line)
        if "error" in out:
            raise RuntimeError(out["error"])
        return (out.get("transcript") or "").strip()


def _to_wsl_path(path: Path) -> str:
    """C:\\Users\\x\\y -> /mnt/c/Users/x/y (relative paths resolved first)"""
    p = str(Path(path).resolve()).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = f"/mnt/{p[0].lower()}{p[2:]}"
    return p


def build_models(frontier: str) -> tuple[list, list[str]]:
    """Returns (models, notes). frontier: gemini | openai | whisper-small.
    If no frontier key materialises, whisper-small substitutes and the
    report says so honestly."""
    notes: list[str] = []
    models: list = [
        SaharaBench(),
        SaharaRawBench(),
        WhisperLocalBench("large-v3"),
        OmnilingualBench(),
    ]
    if frontier == "openai" and os.environ.get("OPENAI_API_KEY"):
        models.append(OpenAiBench())
    elif frontier == "gemini" and os.environ.get("GEMINI_API_KEY"):
        models.append(GeminiBench())
    else:
        models.append(WhisperLocalBench("small"))
        notes.append(
            "No frontier API key was available; whisper-small substitutes as the "
            "frontier model. This is a weaker baseline than Gemini/GPT-4o-transcribe."
        )
    return models, notes
