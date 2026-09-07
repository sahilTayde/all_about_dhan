#!/usr/bin/env python3
"""ASR-only worker: process any CF m4a that lacks a full transcript. No network."""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

BASE = Path("/Users/sahiltayde/Documents/all_about_dhan")
spec = importlib.util.spec_from_file_location(
    "cf_batch", BASE / "data/recon/cf_asr_overnight_batch.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

AUDIO = BASE / "data/transcripts/external_chart_fanatics/audio"
STATE = BASE / "data/recon/cf_asr_overnight_state.json"
LOG = BASE / "data/recon/cf_asr_worker.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    # Poll until prefetch done marker OR idle timeout with no pending
    idle_rounds = 0
    while True:
        state = mod.load_state()
        pending = []
        for m4a in sorted(AUDIO.glob("*.m4a")):
            vid = m4a.stem
            if vid not in mod.DEFAULT_IDS and vid != "jsUTbjwpFVk":
                # only fail-queue (+ already done)
                if vid not in mod.DEFAULT_IDS:
                    continue
            if mod.already_full(vid):
                continue
            if m4a.stat().st_size < 100_000:
                continue
            pending.append(vid)

        if not pending:
            idle_rounds += 1
            prefetch_done = (BASE / "data/recon/cf_prefetch_audio.log").exists() and (
                "PREFETCH done" in (BASE / "data/recon/cf_prefetch_audio.log").read_text(encoding="utf-8", errors="ignore")
            )
            log(f"no pending audio idle={idle_rounds} prefetch_done={prefetch_done}")
            if prefetch_done and idle_rounds >= 3:
                log("exiting — prefetch done and nothing left")
                break
            if idle_rounds >= 120:  # ~60 min idle
                log("exiting — long idle")
                break
            time.sleep(30)
            continue

        idle_rounds = 0
        vid = pending[0]
        log(f"ASR start {vid} (pending={len(pending)})")
        status = mod.process_one(vid, state)
        log(f"ASR done {vid} status={status}")
        # small pause between ASR jobs
        time.sleep(5)

    state = mod.load_state()
    log(f"FINAL succeeded={state.get('succeeded')} failed={state.get('failed')}")


if __name__ == "__main__":
    main()
