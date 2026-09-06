"""FastAPI entry: health + mock paper desk (dashboard shape) + optional feed proxy."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.config import load_api_settings
from api.models import PaperDesk, TookTradeBody, TookTradeRecord
from api.store import SignalStore
from api.ws import router as ws_router


def create_app() -> FastAPI:
    settings = load_api_settings()
    app = FastAPI(
        title=settings.title,
        version="0.1.0",
        description=(
            "DhanHQ-only skeleton. Paper desk JSON is MOCK for dashboard wiring. "
            "No strategy. No live orders."
        ),
    )
    app.state.settings = settings
    app.state.store = SignalStore()

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
        }

    def _desk() -> PaperDesk:
        store: SignalStore = app.state.store
        return store.paper_desk()

    @app.get("/paper/signal", response_model=PaperDesk)
    def paper_signal() -> PaperDesk:
        """Canonical dashboard route (apps/web fetchPaperDesk)."""
        return _desk()

    @app.get("/signals", response_model=PaperDesk)
    def list_signals() -> PaperDesk:
        """Same document as /paper/signal — dashboard shape, not a strategy feed."""
        return _desk()

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

        Includes MIX-DEFAULT-BUY (customer ticket path) and MIX-CLUB-GR (PAPER_WATCH
        parallel). Orders refused. Not a fill.
        """
        snap = getattr(app.state, "live_paper", None)
        if not snap:
            return {
                "kind": "paper_signal",
                "orders": "refused",
                "customer_default_mix": "MIX-DEFAULT-BUY",
                "paper_watch_mixes": ["MIX-CLUB-GR"],
                "underlyings": {},
                "books": {},
                "note": (
                    "Connect /ws/signals?live=1 for Dhan ticks. "
                    "MIX-CLUB-GR paper-watches in parallel. Not a fill."
                ),
            }
        return snap

    app.include_router(ws_router)
    return app


app = create_app()
