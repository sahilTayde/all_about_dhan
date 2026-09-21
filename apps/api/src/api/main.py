"""FastAPI entry: health + mock paper desk (dashboard shape) + optional feed proxy."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.config import load_api_settings
from api.desk_merge import merge_live_paper_into_desk
from api.founder_status import build_founder_status
from api.models import TookTradeBody, TookTradeRecord
from api.premium_bind import bind_premiums_onto_desk
from api.store import SignalStore
from api.ws import router as ws_router


def create_app() -> FastAPI:
    settings = load_api_settings()
    app = FastAPI(
        title=settings.title,
        version="0.1.0",
        description=(
            "DhanHQ-only skeleton. Paper desk JSON is MOCK until /ws/signals "
            "LIVE PAPER overlays premiums. No strategy. No live orders."
        ),
    )
    app.state.settings = settings
    app.state.store = SignalStore()
    app.state.live_paper = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        dhan = settings.dhan
        return {
            "ok": True,
            "service": "all_about_dhan-api",
            "broker": "DhanHQ",
            "dry_run": dhan.dry_run,
            "dhan": {
                "client_id_set": bool(dhan.credentials.client_id),
                "access_token_set": bool(dhan.credentials.access_token),
            },
            "paper_live": bool(getattr(app.state, "live_paper", None)),
            "orders": "refused",
        }

    @app.get("/founder/status")
    def founder_status() -> dict:
        """D4 /pm board. Disk + ports only. Never returns tokens."""
        return build_founder_status()

    def _desk(*, bind_premium: bool = True) -> dict[str, Any]:
        store: SignalStore = app.state.store
        live = getattr(app.state, "live_paper", None)
        merged = merge_live_paper_into_desk(store.paper_desk(), live)
        # When live WS already bound premiums, skip duplicate chain calls.
        live_has_premium = False
        if live and isinstance(live, dict):
            for row in (live.get("underlyings") or {}).values():
                if isinstance(row, dict) and row.get("entry") not in (None, "", "DATA_INSUFFICIENT"):
                    live_has_premium = True
                    break
        if bind_premium and not live_has_premium and not settings.dhan.dry_run:
            merged = bind_premiums_onto_desk(merged, prefer_live=True)
        elif bind_premium and settings.dhan.dry_run:
            meta = dict(merged.get("meta") or {})
            meta.setdefault(
                "premium_gaps",
                [
                    "DATA_INSUFFICIENT: Dhan dry_run / tokens empty — OPTIDX premium not fetched"
                ],
            )
            meta.setdefault("premium_bind", "DATA_INSUFFICIENT")
            merged["meta"] = meta
        return merged

    @app.get("/paper/signal")
    def paper_signal() -> dict[str, Any]:
        """Canonical dashboard route (apps/web fetchPaperDesk)."""
        return _desk(bind_premium=True)

    @app.get("/signals")
    def list_signals() -> dict[str, Any]:
        """Same document as /paper/signal — dashboard shape, not a strategy feed."""
        return _desk(bind_premium=True)

    @app.post("/signals/{signal_id}/took-trade", response_model=TookTradeRecord)
    def took_trade(signal_id: str, body: TookTradeBody) -> TookTradeRecord:
        store: SignalStore = app.state.store
        rec = store.record_took_trade(
            signal_id,
            body.took_trade,
            lots=body.lots,
            spot=body.spot,
            reported_pnl=body.reported_pnl,
        )
        if rec is None:
            raise HTTPException(status_code=404, detail="signal not found")
        return rec

    @app.get("/paper/live-signals")
    def paper_live_signals() -> dict:
        """Last paper-signal snapshot from /ws/signals. Empty until a client connected.

        Includes MIX-DEFAULT-BUY (customer ticket path). MIX-CLUB-GR is PARKED
        on the working ticket (KEEP_ALL). MIX-CF / Okala notify removed.
        """
        snap = getattr(app.state, "live_paper", None)
        if not snap:
            return {
                "kind": "paper_signal",
                "orders": "refused",
                "customer_default_mix": "MIX-DEFAULT-BUY",
                "paper_watch_mixes": [],
                "underlyings": {},
                "books": {},
                "note": (
                    "Connect /ws/signals?live=1 for Dhan ticks + optionchain premium bind. "
                    "MIX-CLUB-GR PARKED working path. Not a fill."
                ),
            }
        return snap

    @app.get("/paper/sod-exam")
    def paper_sod_exam() -> dict[str, Any]:
        """06 honesty exam JSON (recon or mock). Not a promote. No orders."""
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[4]
        recon = root / "data" / "recon" / "sod_exam_report.json"
        mock = root / "apps" / "web" / "public" / "mock" / "sod_exam_report.json"
        path = recon if recon.is_file() else mock
        if not path.is_file():
            return {
                "ok": False,
                "reason": "DATA_INSUFFICIENT: run python -m desk_ml sod-exam",
                "orders": "REFUSED",
                "promote": False,
                "win_rate": None,
                "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
                "how_to_read": {
                    "where": "Founder /pm → Honesty exam",
                    "when": "After close: python -m desk_ml sod-exam",
                },
            }
        blob = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(blob, dict):
            blob.setdefault("orders", "REFUSED")
            blob.setdefault("promote", False)
            blob.setdefault("win_rate", None)
            blob["source_path"] = str(path.name)
        return blob

    @app.get("/paper/ml-books")
    def paper_ml_books() -> dict[str, Any]:
        """Parallel ML/dealer PAPER scalper board. Net ₹ after Groww+STT. NO_PROMOTE."""
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[4]
        recon = root / "data" / "recon" / "ml_paper_dashboard.json"
        mock = root / "apps" / "web" / "public" / "mock" / "ml_paper_dashboard.json"
        path = recon if recon.is_file() else mock
        if not path.is_file():
            return {
                "ok": False,
                "reason": "DATA_INSUFFICIENT: run python -m desk_ml paper-scalp --replay",
                "orders": "REFUSED",
                "promote": False,
                "win_rate": None,
                "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
            }
        blob = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(blob, dict):
            blob.setdefault("orders", "REFUSED")
            blob.setdefault("promote", False)
            blob.setdefault("win_rate", None)
        return blob

    @app.get("/paper/backtests/itm-scalp")
    def paper_itm_scalp_backtest() -> dict[str, Any]:
        """Last MIX-ITM-OPT-SCALP paper backtest JSON (recon). Not a promote."""
        import json
        from pathlib import Path

        path = Path(__file__).resolve().parents[4] / "data" / "recon" / "itm_scalp_backtest.json"
        if not path.is_file():
            return {
                "ok": False,
                "reason": "DATA_INSUFFICIENT: run python -m backtest_engine --live itm-scalp",
                "orders": "refused",
                "promotion": "NO_PROMOTE",
            }
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/paper/backtests/itm-champions")
    def paper_itm_champions_board() -> dict[str, Any]:
        """PAPER champion leaderboard (wins / streaks / P/L). Not a promote. No orders."""
        import json
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[4]
            / "data"
            / "recon"
            / "itm_champion_leaderboard.json"
        )
        if not path.is_file():
            return {
                "ok": False,
                "reason": (
                    "DATA_INSUFFICIENT: run "
                    "python -m backtest_engine.run_itm_champions"
                ),
                "orders": "refused",
                "promotion": "NO_PROMOTE",
                "live_auto_trade": "REFUSED",
            }
        return json.loads(path.read_text(encoding="utf-8"))

    app.include_router(ws_router)
    return app


app = create_app()
