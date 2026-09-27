"""Wall-clock timeouts for every one-shot job (REG-10 / architecture §5.1).

V2-04 owns the full kernel ``run_with_deadline``; this module is the V2-15
registry so every job unit has a timeout before that ticket lands.
Partial output is written to ``*.tmp`` and renamed only on success.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

# Defaults until config/v2/engine.yaml jobs: exists (V2-04). Seconds.
JOBS: dict[str, int] = {
    "replay": 600,
    "forward-eval": 1800,
    "etl": 1800,
    "bench-legacy": 600,
    "pre-market": 900,
    "backup": 300,
}


class JobTimeout(Exception):
    def __init__(self, job: str, timeout_s: float) -> None:
        super().__init__(f"{job} exceeded {timeout_s}s")
        self.job = job
        self.timeout_s = timeout_s


def run_with_deadline(fn: Callable[[], T], timeout_s: float, *, job: str = "job") -> T:
    """Run ``fn``; on timeout raise JobTimeout and leave no published output."""
    box: list[tuple[str, T | BaseException]] = []

    def _run() -> None:
        try:
            box.append(("ok", fn()))
        except BaseException as exc:  # noqa: BLE001 — surface to caller
            box.append(("err", exc))

    thread = threading.Thread(target=_run, name=f"deadline-{job}", daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        raise JobTimeout(job, timeout_s)
    if not box:
        raise JobTimeout(job, timeout_s)
    kind, payload = box[0]
    if kind == "err":
        raise payload  # type: ignore[misc]
    return payload  # type: ignore[return-value]


def publish_atomic(dest: Path, body: str) -> None:
    """Write dest via sibling .tmp; caller deletes .tmp on JobTimeout."""
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(dest)
