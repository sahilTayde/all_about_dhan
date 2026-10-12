"""Recorder disk housekeeping (Mac). gzip finished prior-day tape files and alert on low free space.

  python -m marketdata.housekeeping --tape-root data/tape/v2 [--keep-days 1] [--min-free-gb 30]
Never touches today's (IST) folder; each .jsonl is replaced by .jsonl.gz only after the gzip is verified
(size + sha256 of the decompressed bytes). Exit 2 + ALERT line when free space < --min-free-gb.
With 20-level depth + all near-ATM strikes, files may reach ~10 GB/day; the Mac had 116 GB free.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))


def _sha(path: Path, opener=open) -> str:
    h = hashlib.sha256()
    with opener(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gzip_prior_days(tape_root: Path, today: str, keep_days: int = 1) -> list[str]:
    """gzip *.jsonl in day folders older than today - (keep_days - 1). Returns the files compressed."""
    cutoff = (datetime.fromisoformat(today) - timedelta(days=max(keep_days - 1, 0))).date().isoformat()
    done = []
    for day_dir in sorted(p for p in Path(tape_root).iterdir() if p.is_dir() and not p.is_symlink()):
        if not (len(day_dir.name) == 10 and day_dir.name < cutoff):
            continue
        for f in sorted(day_dir.glob("*.jsonl")):
            gz = f.with_suffix(".jsonl.gz")
            tmp = gz.with_suffix(".gz.tmp")
            with f.open("rb") as src, gzip.open(tmp, "wb", compresslevel=6) as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            if _sha(f) != _sha(tmp, gzip.open):
                tmp.unlink()
                raise RuntimeError(f"gzip verify failed: {f}")
            os.replace(tmp, gz)
            f.unlink()
            done.append(str(gz))
    return done


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / 1e9


def disk_alert(path: Path, min_free_gb: float = 30.0, free: float | None = None) -> str | None:
    gb = free_gb(path) if free is None else free
    return f"ALERT: only {gb:.1f} GB free on the recorder disk (< {min_free_gb:g} GB)." if gb < min_free_gb else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tape-root", required=True)
    ap.add_argument("--keep-days", type=int, default=1)
    ap.add_argument("--min-free-gb", type=float, default=30.0)
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    root = Path(a.tape_root)
    today = a.today or datetime.now(IST).date().isoformat()
    for f in gzip_prior_days(root, today, a.keep_days):
        print("gzipped", f)
    alert = disk_alert(root, a.min_free_gb)
    print(alert or f"OK: {free_gb(root):.1f} GB free")
    return 2 if alert else 0


if __name__ == "__main__":
    sys.exit(main())
