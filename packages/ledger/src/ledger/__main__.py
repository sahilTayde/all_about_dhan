"""python -m ledger migrate|ping|export. Paper only. No live broker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ledger.migrate import CODE_SCHEMA_VERSION, migrate
from ledger.postgres import StoreConfigError, health_ping, load_store_config, redact_dsn


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ledger v2 migrations / ping / postgres cutover (paper only)")
    sub = p.add_subparsers(dest="command", required=True)

    m = sub.add_parser("migrate", help="Apply pending SQL. Fail-closed. Never auto on legacy path.")
    m.add_argument("--path", help="SQLite file")
    m.add_argument("--dsn", help="Postgres STATE_DSN (overrides --path when set)")
    m.add_argument("--allow-legacy", action="store_true")

    ping = sub.add_parser("ping", help="Health ping (SELECT 1). Fail-closed on postgres without DSN.")
    ping.add_argument("--dsn")
    ping.add_argument("--path")

    exp = sub.add_parser("export", help="Row-by-row sqlite → postgres with counts and checksums")
    exp.add_argument("--to", required=True, choices=("postgres",))
    exp.add_argument("--from", dest="source", required=True, help="SQLite source path")
    exp.add_argument("--dsn", help="Destination STATE_DSN")

    args = p.parse_args(argv)
    if args.command == "migrate":
        if args.dsn:
            ver = migrate(args.dsn, dsn=args.dsn)
        elif args.path:
            ver = migrate(Path(args.path), allow_legacy=args.allow_legacy)
        else:
            cfg = load_store_config()
            if cfg.engine == "postgres":
                ver = migrate(cfg.dsn, dsn=cfg.dsn)
            else:
                ver = migrate(Path(cfg.sqlite_path), allow_legacy=args.allow_legacy)
        print(json.dumps({"ok": True, "schema_version": ver, "code_version": CODE_SCHEMA_VERSION}))
        return 0
    if args.command == "ping":
        if args.dsn:
            print(json.dumps(health_ping(args.dsn)))
            return 0
        if args.path:
            from ledger.v2 import SqliteLedgerStore

            store = SqliteLedgerStore(Path(args.path), migrate_schema=True)
            try:
                print(json.dumps(store.health_ping()))
            finally:
                store.close()
            return 0
        cfg = load_store_config()
        if cfg.engine == "postgres":
            print(json.dumps(health_ping(cfg.dsn)))
            return 0
        from ledger.v2 import SqliteLedgerStore

        store = SqliteLedgerStore(Path(cfg.sqlite_path), migrate_schema=True)
        try:
            print(json.dumps(store.health_ping()))
        finally:
            store.close()
        return 0
    dsn = args.dsn or load_store_config().dsn
    if not dsn:
        raise StoreConfigError("export --to postgres requires STATE_DSN")
    from ledger.export import export_sqlite_to_postgres

    report = export_sqlite_to_postgres(Path(args.source), dsn)
    report["dsn"] = redact_dsn(str(report.get("dsn") or dsn))
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
