#!/usr/bin/env python3
"""Overnight Chart Fanatics ASR batch — yt-dlp android → m4a → faster-whisper.

PAPER / SOURCE_FACT only. Education ≠ edge. No MIX/BIND.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/Users/sahiltayde/Documents/all_about_dhan")
CF = BASE / "teams/01_research/docs/chart_fanatics"
RAW = BASE / "data/transcripts/external_chart_fanatics"
AUDIO = RAW / "audio"
QUEUE = BASE / "data/recon/cf_overnight_queue_transcript_retry.json"
STATE = BASE / "data/recon/cf_asr_overnight_state.json"
LOG = CF / "PHASE3K_ASR_LOG.md"

# Fail queue (views desc) from RETRY_TOMORROW.md
DEFAULT_IDS = [
    "xUyqIjCfZzg",
    "SMSqQTBxjc0",
    "Jx5cJ_qb31U",
    "PZDWQgtqt2I",
    "_qeFh1ADss8",
    "52ZsDmFHqyY",
    "jHsD2-2K_Kk",
    "SQEtBHOJW6I",
    "yZpzG8R3Ayk",
    "WDdvnd9vLbM",
    "YzYDUEUOZ4k",
    "VDK200OHNSo",
    "mDNcx2Dhhms",
    "8HxT9WQ-uD0",
    "UIGZtoGGPH4",
    "xl4QHqlBCfk",
    "TyHTEtArsS4",
    "nMhywubR2xc",
    "35cyqDz-ej8",
    "_wpg45NdMkM",
    "9D9ck-ZI6V0",
    "70UtrLU6RAg",
    "EZ_L7zovyrw",
    "4BgkLlwgpvo",
    "0_NSmOWVbpA",
    "2Ug0jyDvoek",
    "SInAfwX3X3A",
    "KkTTCKr-3Ew",
    "EcTRlLYvhXU",
]

PAUSE_BETWEEN_DOWNLOADS_SEC = 60
MAX_DOWNLOAD_ATTEMPTS = 3
CLIENTS = ("android", "ios", "mweb")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {
        "started": utc_now(),
        "succeeded": [],
        "failed": [],
        "skipped_already_full": [],
        "in_progress": None,
        "results": {},
    }


def save_state(state: dict) -> None:
    state["updated"] = utc_now()
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def ffmpeg_bin() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def stub_meta(vid: str) -> dict:
    md_path = CF / f"{vid}_TRANSCRIPT.md"
    md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    title = ""
    if md:
        title = md.splitlines()[0].replace("# Transcript — ", "").strip()
    def grab(pat: str) -> str:
        m = re.search(pat, md)
        return m.group(1).strip() if m else ""

    return {
        "id": vid,
        "title": title or vid,
        "published": grab(r"\*\*Published:\*\*\s*(.+)"),
        "views": grab(r"\*\*Views \(API\):\*\*\s*(.+)"),
        "duration": grab(r"\*\*Duration:\*\*\s*([^\n]+)"),
        "guest_stub": grab(r"\*\*Guest:\*\*\s*(.+)"),
    }


def already_full(vid: str) -> bool:
    asr = RAW / f"{vid}.asr.txt"
    md = CF / f"{vid}_TRANSCRIPT.md"
    if asr.exists() and asr.stat().st_size > 5000:
        return True
    if md.exists():
        text = md.read_text(encoding="utf-8")
        if "Transcript status:** `full`" in text and "[ASR]" in text and len(text) > 8000:
            return True
    return False


def download_audio(vid: str) -> Path:
    AUDIO.mkdir(parents=True, exist_ok=True)
    m4a = AUDIO / f"{vid}.m4a"
    if m4a.exists() and m4a.stat().st_size > 100_000:
        print(f"[{vid}] audio already present: {m4a} ({m4a.stat().st_size} bytes)", flush=True)
        return m4a

    ff = ffmpeg_bin()
    ff_dir = str(Path(ff).parent)
    env = os.environ.copy()
    env["PATH"] = ff_dir + os.pathsep + env.get("PATH", "")
    log_path = AUDIO / f"{vid}_ydlp.log"

    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        for client in CLIENTS:
            print(f"[{vid}] download attempt={attempt} client={client}", flush=True)
            out_tmpl = str(AUDIO / f"{vid}.%(ext)s")
            # Prefer progressive 18 (worked for Phase-3J); fall back to bestaudio
            cmd = [
                "yt-dlp",
                "-f",
                "18/bestaudio/best",
                "--extractor-args",
                f"youtube:player_client={client}",
                "--ffmpeg-location",
                ff_dir,
                "--no-playlist",
                "--proxy",
                "",
                "-o",
                out_tmpl,
                "--newline",
                f"https://www.youtube.com/watch?v={vid}",
            ]
            with log_path.open("a", encoding="utf-8") as lf:
                lf.write(f"\n===== {utc_now()} attempt={attempt} client={client} =====\n")
                lf.flush()
                proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env)
            # Collect any downloaded media
            candidates = list(AUDIO.glob(f"{vid}.*"))
            media = [
                p
                for p in candidates
                if p.suffix.lower() in {".mp4", ".m4a", ".webm", ".mkv", ".mp3", ".opus"}
                and "_ydlp" not in p.name
            ]
            if not media and proc.returncode != 0:
                print(f"[{vid}] client={client} rc={proc.returncode}", flush=True)
                time.sleep(8)
                continue

            # Prefer existing m4a; else extract from mp4/webm
            m4a_hit = next((p for p in media if p.suffix.lower() == ".m4a"), None)
            if m4a_hit and m4a_hit.stat().st_size > 100_000:
                if m4a_hit != m4a:
                    m4a_hit.rename(m4a)
                print(f"[{vid}] got m4a {m4a.stat().st_size}", flush=True)
                return m4a

            src = next((p for p in media if p.suffix.lower() in {".mp4", ".webm", ".mkv"}), None)
            if src:
                print(f"[{vid}] extracting audio from {src.name}", flush=True)
                # Try stream copy AAC first; fall back to re-encode
                for extract_cmd in (
                    [ff, "-y", "-i", str(src), "-vn", "-acodec", "copy", str(m4a)],
                    [ff, "-y", "-i", str(src), "-vn", "-c:a", "aac", "-b:a", "128k", str(m4a)],
                ):
                    r = subprocess.run(extract_cmd, capture_output=True, text=True)
                    if r.returncode == 0 and m4a.exists() and m4a.stat().st_size > 100_000:
                        try:
                            src.unlink()
                        except OSError:
                            pass
                        print(f"[{vid}] extracted m4a {m4a.stat().st_size}", flush=True)
                        return m4a
                print(f"[{vid}] ffmpeg extract failed", flush=True)

            # Direct audio formats
            for p in media:
                if p.suffix.lower() in {".webm", ".opus", ".mp3"}:
                    r = subprocess.run(
                        [ff, "-y", "-i", str(p), "-vn", "-c:a", "aac", "-b:a", "128k", str(m4a)],
                        capture_output=True,
                        text=True,
                    )
                    if r.returncode == 0 and m4a.exists() and m4a.stat().st_size > 100_000:
                        try:
                            p.unlink()
                        except OSError:
                            pass
                        return m4a
            time.sleep(8)
        time.sleep(20)

    raise RuntimeError(f"download failed after retries: {vid}")


def run_asr(vid: str, audio: Path) -> dict:
    from faster_whisper import WhisperModel

    raw_txt = RAW / f"{vid}.asr.txt"
    meta_path = AUDIO / f"{vid}.asr_meta.json"
    log_path = AUDIO / f"{vid}.asr.log"

    def log(msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log_path.write_text("", encoding="utf-8")
    log(f"Loading WhisperModel base int8 CPU for {vid}...")
    t0 = time.time()
    # Prefer local cache; allow download if missing
    try:
        model = WhisperModel("base", device="cpu", compute_type="int8", local_files_only=True)
    except Exception:
        model = WhisperModel("base", device="cpu", compute_type="int8")
    log(f"Model ready in {time.time() - t0:.1f}s")
    log(f"Transcribing {audio} ...")
    t1 = time.time()
    segments, info = model.transcribe(
        str(audio), language="en", vad_filter=True, beam_size=1
    )
    parts = []
    seg_count = 0
    last_end = 0.0
    for seg in segments:
        parts.append(seg.text.strip())
        seg_count += 1
        last_end = seg.end
        if seg_count % 50 == 0:
            log(f"  segments={seg_count} last_end={seg.end:.1f}s")
    text = "\n".join(p for p in parts if p)
    raw_txt.write_text(text + ("\n" if text else ""), encoding="utf-8")
    elapsed = time.time() - t1
    meta = {
        "video_id": vid,
        "tool": "faster-whisper",
        "model": "base",
        "device": "cpu",
        "compute_type": "int8",
        "source": "ASR_WHISPER",
        "language": info.language,
        "language_probability": info.language_probability,
        "audio_duration_sec": getattr(info, "duration", None),
        "last_segment_end_sec": last_end,
        "segment_count": seg_count,
        "char_count": len(text),
        "elapsed_sec": round(elapsed, 1),
        "audio_path": str(audio),
        "raw_txt": str(raw_txt),
        "retrieved": utc_now(),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"DONE segments={seg_count} chars={len(text)} elapsed={elapsed:.1f}s")
    return meta


def sniff_guest(text: str, stub_guest: str) -> str:
    head = "\n".join(text.splitlines()[:80])
    patterns = [
        (r"Fabio\s+Valentini|Fabio", "Fabio Valentini"),
        (r"Carmine\s+Rosato|Carmine", "Carmine Rosato"),
        (r"Tanja|Tanya", "Tanja"),
        (r"Anthony", "Anthony"),
        (r"Market Wizard", "Market Wizard guest (ASR)"),
    ]
    for pat, name in patterns:
        if re.search(pat, head, re.I):
            return name
    return (stub_guest or "UNKNOWN (from title/stub)").split("\n")[0][:80]


def write_transcript_md(vid: str, meta: dict, info: dict) -> Path:
    raw = (RAW / f"{vid}.asr.txt").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    paras, buf = [], []
    for i, ln in enumerate(lines, 1):
        buf.append(ln)
        if i % 5 == 0:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    body = "\n\n".join(paras)
    guest = sniff_guest(raw, info.get("guest_stub", ""))
    asr_sec = float(meta.get("audio_duration_sec") or meta.get("last_segment_end_sec") or 0)
    asr_h = int(asr_sec // 3600)
    asr_m = int((asr_sec % 3600) // 60)
    asr_s = asr_sec % 60
    asr_human = f"{asr_h}h{asr_m:02d}m{asr_s:04.1f}s" if asr_h else f"{asr_m}m{asr_s:04.1f}s"
    dur_field = info.get("duration") or ""
    # duration line already includes ISO in stubs like: 1h12m19s (`PT1H12M19S`)
    if "`" in dur_field:
        duration_line = f"{dur_field} · **ASR processed:** {asr_sec:.1f}s (~{asr_human})"
    else:
        duration_line = f"{dur_field or 'UNKNOWN'} · **ASR processed:** {asr_sec:.1f}s (~{asr_human})"

    published_line = ""
    if info.get("published"):
        published_line = f"**Published:** {info['published']}  \n"

    header = f"""# Transcript — {info.get('title') or vid}

**Channel:** Chart Fanatics (`@chart-fanatics` / `UC2GyeAMRDA4cRIiISejML2g`)  
**Video ID:** `{vid}`  
**URL:** https://www.youtube.com/watch?v={vid}  
{published_line}**Views (API):** {info.get('views') or 'UNKNOWN'}  
**Duration:** {duration_line}  
**Guest:** {guest}  
**Transcript status:** `full`  
**Fetch method:** Phase-3K **audio download → local ASR** (YouTube captions still IpBlocked/429 on this host; overnight retry 2026-09-07)  
**Source:** `ASR_WHISPER` via **faster-whisper** model=`base` device=`cpu` compute=`int8` — **not** YouTube caption / timedtext  
**Quality:** `[ASR]` — automatic speech recognition; expect name/term errors (futures jargon, proper nouns). Education ≠ edge.  
**Timed VTT:** `DATA_INSUFFICIENT` (ASR plain text only)  
**Layer:** `SOURCE_FACT` (ASR) — education ≠ edge. **Not** DHAN-DERIVED. **Keep separate** from `@iqcapital_io` / STRAT-001–014.  
**Retrieved:** {meta.get('retrieved') or utc_now()}  
**Chars (collapsed):** {len(body)}  
**Audio:** `data/transcripts/external_chart_fanatics/audio/{vid}.m4a`  
**Raw ASR:** `data/transcripts/external_chart_fanatics/{vid}.asr.txt`

---

## Caption text

[ASR] The following text is local speech-to-text (faster-whisper), **not** an official YouTube caption track.

"""
    out = CF / f"{vid}_TRANSCRIPT.md"
    out.write_text(header + body + "\n", encoding="utf-8")
    return out


def process_one(vid: str, state: dict) -> str:
    if already_full(vid):
        print(f"[{vid}] already full — skip", flush=True)
        if vid not in state["skipped_already_full"] and vid not in state["succeeded"]:
            state["skipped_already_full"].append(vid)
        save_state(state)
        return "skip"

    state["in_progress"] = vid
    save_state(state)
    info = stub_meta(vid)
    try:
        audio = download_audio(vid)
        meta = run_asr(vid, audio)
        if int(meta.get("char_count") or 0) < 500:
            raise RuntimeError(f"ASR too short: {meta.get('char_count')}")
        write_transcript_md(vid, meta, info)
        state["results"][vid] = {"ok": True, **{k: meta.get(k) for k in ("char_count", "elapsed_sec", "audio_duration_sec")}}
        if vid not in state["succeeded"]:
            state["succeeded"].append(vid)
        if vid in state["failed"]:
            state["failed"] = [x for x in state["failed"] if x != vid]
        state["in_progress"] = None
        save_state(state)
        print(f"[{vid}] SUCCESS chars={meta.get('char_count')}", flush=True)
        return "ok"
    except Exception as e:
        print(f"[{vid}] FAIL: {e}", flush=True)
        state["results"][vid] = {"ok": False, "error": str(e), "at": utc_now()}
        if vid not in state["failed"]:
            state["failed"].append(vid)
        state["in_progress"] = None
        save_state(state)
        # leave / update stub skip note
        stub = CF / f"{vid}_TRANSCRIPT.md"
        note = (
            f"\n\n---\n\n## Overnight ASR retry note ({utc_now()})\n\n"
            f"- Attempted Phase-3K ASR path (yt-dlp android → m4a → faster-whisper).\n"
            f"- **Result:** FAIL — `{e}`\n"
            f"- Stub retained for founder wake-up. Education ≠ edge.\n"
        )
        if stub.exists():
            text = stub.read_text(encoding="utf-8")
            if "Overnight ASR retry note" not in text:
                stub.write_text(text.rstrip() + note, encoding="utf-8")
        return "fail"


def main() -> int:
    ids = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_IDS
    # Prefer shorter videos first for early wins, but keep founder queue order if env set
    order = os.environ.get("CF_ASR_ORDER", "queue")  # queue | short_first
    if order == "short_first":
        # rough: sort by existing stub duration string length proxy — use views queue still
        # Better: parse ISO duration from stubs
        def dur_sec(vid: str) -> int:
            d = stub_meta(vid).get("duration") or ""
            m = re.search(r"`PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?`", d)
            if not m:
                return 10**9
            h = int(m.group(1) or 0)
            mi = int(m.group(2) or 0)
            s = int(m.group(3) or 0)
            return h * 3600 + mi * 60 + s

        ids = sorted(ids, key=dur_sec)

    AUDIO.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    state = load_state()
    print(f"Phase-3K overnight ASR: {len(ids)} ids order={order}", flush=True)

    for i, vid in enumerate(ids):
        print(f"\n==== [{i+1}/{len(ids)}] {vid} ====", flush=True)
        status = process_one(vid, state)
        if status == "ok" and i < len(ids) - 1:
            # rate-limit hygiene between downloads
            print(f"Sleeping {PAUSE_BETWEEN_DOWNLOADS_SEC}s before next…", flush=True)
            time.sleep(PAUSE_BETWEEN_DOWNLOADS_SEC)
        elif status == "fail" and i < len(ids) - 1:
            print("Sleeping 30s after fail…", flush=True)
            time.sleep(30)

    print("\n==== SUMMARY ====", flush=True)
    print("succeeded", state["succeeded"], flush=True)
    print("failed", state["failed"], flush=True)
    print("skipped", state["skipped_already_full"], flush=True)
    save_state(state)
    return 0 if not state["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
