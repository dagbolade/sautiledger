"""Persistent omnilingual-ASR worker — runs INSIDE WSL (fairseq2 ships no
Windows wheels). Loads the model once, then serves clips over stdin/stdout
as JSON lines: {"path": "/mnt/c/...", "lang": "pcm_Latn"} in,
{"transcript": "..."} (or {"error": "..."}) out.

Launched by bench_asr.OmnilingualBench:
  wsl -d Ubuntu-24.04 -- bash -lc \
    "cd ~ && LD_LIBRARY_PATH=~/omni/shimlib ./omni/bin/python <this file> <model_card>"
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    model_card = sys.argv[1] if len(sys.argv) > 1 else "omniASR_CTC_300M"
    from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

    pipe = ASRInferencePipeline(model_card=model_card, device="cpu")
    print(json.dumps({"ready": True, "model": model_card}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            out = pipe.transcribe([req["path"]], lang=[req["lang"]], batch_size=1)
            print(json.dumps({"transcript": out[0]}, ensure_ascii=False), flush=True)
        except Exception as exc:  # keep serving; the harness decides what to do
            print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), flush=True)


if __name__ == "__main__":
    main()
