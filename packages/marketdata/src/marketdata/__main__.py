"""Market data recorder CLI (V2-D2). Record only; places no orders.

    python -m marketdata --record-only [--underlying NIFTY] [--tape-root PATH]
    python -m marketdata --coverage YYYY-MM-DD [--tape-root PATH]

Credentials: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN from the environment or the repo ``.env``.
Exit codes: 0 clean stop (15:30 IST or Ctrl-C/SIGTERM), 1 unexpected error,
2 credentials or startup failure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import logging.handlers
import queue
import signal
import sys
from datetime import date
from pathlib import Path

from dhan_client.config import load_settings, repo_root
from dhan_client.errors import CredentialsError

from marketdata import logsafe
from marketdata.clock import LiveClock, session_day
from marketdata.config import RecorderConfig
from marketdata.coverage import write_summary
from marketdata.instruments import UNDERLYINGS, DhanInstrumentSource, StartupError
from marketdata.recorder import MarketDataRecorder

log = logging.getLogger("marketdata")


def setup_logging(log_file: Path | None) -> logging.handlers.QueueListener:
    """Log to stderr (and ``log_file``) from a background thread: the event loop only enqueues,
    so a slow disk or terminal never delays packet handling. Credentials are redacted."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    formatter = logsafe.RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for handler in handlers:
        handler.setFormatter(formatter)
    records: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    listener = logging.handlers.QueueListener(records, *handlers, respect_handler_level=True)
    listener.start()
    enqueue = logging.handlers.QueueHandler(records)
    enqueue.setFormatter(logging.Formatter("%(message)s"))  # the listener's handlers do the real format
    logging.basicConfig(level=logging.INFO, handlers=[enqueue], force=True)
    # At DEBUG the websockets client logs the feed URL, which carries the token; it is also
    # redacted by logsafe if someone turns DEBUG back on.
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logsafe.install()
    return listener


async def run_recorder(recorder: MarketDataRecorder) -> int:
    """Run until 15:30 IST, Ctrl-C or SIGTERM; returns the exit code."""
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, recorder.request_stop, f"signal {sig.name}")
    try:
        return await recorder.run()
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m marketdata", description=__doc__.splitlines()[0])
    parser.add_argument("--record-only", action="store_true", help="record depth, quotes and OI cadence")
    parser.add_argument("--underlying", default="NIFTY", choices=sorted(UNDERLYINGS))
    parser.add_argument("--tape-root", type=Path, default=None, help="default: <repo>/data/tape/v2")
    parser.add_argument("--coverage", metavar="YYYY-MM-DD", help="recompute coverage_summary.json for a day")
    args = parser.parse_args(argv)

    root = repo_root()
    tape_root: Path = args.tape_root or root / "data" / "tape" / "v2"
    if args.coverage:
        day = date.fromisoformat(args.coverage)
        path = write_summary(tape_root / day.isoformat(), day)
        summary = json.loads(path.read_text(encoding="utf-8"))
        print(f"{path}: failing={summary['failing']}")
        return 0
    if not args.record_only:
        parser.error("pass --record-only (the recorder runs standalone, without the engine)")

    day = session_day(LiveClock().now())
    listener = setup_logging(tape_root / day.isoformat() / "recorder.log")
    try:
        return _record(args.underlying, root, tape_root, day)
    finally:
        listener.stop()


def _record(underlying: str, root: Path, tape_root: Path, day: date) -> int:
    try:
        settings = load_settings(dry_run=False)
    except CredentialsError:
        log.error(
            "live recording needs DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN (export them or put them in %s)",
            root / ".env",
        )
        return 2
    cache_dir = root / "data" / "cache" / "marketdata"
    source = DhanInstrumentSource(settings, cache_dir, day=day)
    config = RecorderConfig(tape_root=tape_root, underlying=underlying, cache_dir=cache_dir)
    recorder = MarketDataRecorder(config, settings, source=source)
    log.info("marketdata recorder: %s, session %s, tapes under %s", underlying, day, tape_root)
    try:
        return asyncio.run(run_recorder(recorder))
    except (StartupError, CredentialsError) as exc:
        log.error("startup failed: %s", exc)
        return 2
    except KeyboardInterrupt:
        return 0
    except Exception:
        log.exception("recorder crashed")
        return 1
    finally:
        source.close()


if __name__ == "__main__":
    sys.exit(main())
