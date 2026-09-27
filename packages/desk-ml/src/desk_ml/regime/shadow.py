"""Boss-side regime runner: labels, adaptive weights and the intermarket overlay next to the static picker.

`boss_hook(engine, step, votes, picker)` is called by `paper_scalp.step_decide` right after the static
`picker_majority`, on both the legacy and the USE_EVENT_BUS path. In `shadow` mode (default) it
returns the static picker unchanged, so trades are byte-identical; it only labels the minute,
computes the weighted decision and the overlay, logs them, and publishes REGIME_LABEL / BOSS_SHADOW
on the event bus when the engine has one. In `apply` mode it returns the weighted decision instead.

Causality: labels use completed 1m bars only; weights change only when a trade has CLOSED
(`engine.closed`) or a vote's horizon bar has completed. Nothing reads data after the tick.

Default runs never write files. Weight state is loaded read-only; the replay report script
(`scripts/regime_shadow_report.py --save-state`) is the only writer.
"""

from __future__ import annotations

import json
import logging
import math
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

from desk_ml.regime.intermarket import overlay_decision, regime_for_session
from desk_ml.regime.labels import IST, UNKNOWN, LabelConfig, RegimeLabeller
from desk_ml.regime.weights import WeightConfig, WeightState, weighted_picker

log = logging.getLogger("desk_ml.regime")

CONFIG_PATH = Path("config") / "regime.yaml"
MODES = ("off", "shadow", "apply")
FLIP_SUPPRESS = "suppress"  # static TICKET -> shadow HOLD
FLIP_NEW = "new"  # static HOLD -> shadow TICKET
FLIP_REVERSE = "reverse"  # CE <-> PE
FLIP_KINDS = (FLIP_SUPPRESS, FLIP_NEW, FLIP_REVERSE)

# None = build one per engine from config/regime.yaml; False = forced off (report's identity check).
_RUNNER: ContextVar[Any] = ContextVar("aad_regime_shadow", default=None)
_warned: set[str] = set()


@dataclass(frozen=True)
class RegimeConfig:
    mode: str = "shadow"
    labels: LabelConfig = field(default_factory=LabelConfig)
    intermarket: dict = field(default_factory=dict)
    weights: WeightConfig = field(default_factory=WeightConfig)
    overlay: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Optional[Mapping[str, Any]]) -> "RegimeConfig":
        raw = dict(raw or {})
        mode = str(raw.get("mode", "shadow")).strip().lower()
        if mode not in MODES:
            raise ValueError(f"config/regime.yaml mode must be one of {MODES}, got {mode!r}")
        return cls(
            mode=mode,
            labels=LabelConfig.from_dict(raw.get("labels")),
            intermarket=dict(raw.get("intermarket") or {}),
            weights=WeightConfig.from_dict(raw.get("weights")),
            overlay=dict(raw.get("overlay") or {}),
        )


def load_config(root: Optional[Path] = None, path: Optional[Path] = None) -> RegimeConfig:
    """`config/regime.yaml` under `root`, else under this checkout. Missing file = defaults (shadow)."""
    from desk_ml.persist import repo_root

    candidates = [Path(path)] if path else [Path(root or repo_root()) / CONFIG_PATH, repo_root() / CONFIG_PATH]
    for p in candidates:
        if p.is_file():
            import yaml

            return RegimeConfig.from_dict(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return RegimeConfig()


@contextmanager
def use_runner(runner: Any) -> Iterator[Any]:
    """Route every `boss_hook` call in this context to `runner`; `False` turns the hook off."""
    token = _RUNNER.set(runner)
    try:
        yield runner
    finally:
        _RUNNER.reset(token)


def boss_hook(engine: Any, step: Any, votes: Sequence[Any], picker: dict[str, Any]) -> dict[str, Any]:
    """Never raises and never changes `picker` unless mode is `apply`."""
    try:
        runner = _RUNNER.get()
        if runner is False:
            return picker
        if runner is None:
            runner = engine.__dict__.get("_regime_runner")
            if runner is None:
                cfg = load_config(getattr(engine, "root", None))
                runner = RegimeShadow(cfg, root=getattr(engine, "root", None)) if cfg.mode != "off" else False
                engine.__dict__["_regime_runner"] = runner
        if not runner:
            return picker
        return runner.observe(engine, step, votes, picker)
    except Exception as exc:  # the shadow must never stop the desk
        key = type(exc).__name__
        if key not in _warned:
            _warned.add(key)
            log.exception("regime shadow failed; static picker kept")
        return picker


def _finite(x: Any) -> Any:
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_finite(v) for v in x]
    return x


def _decision(p: Mapping[str, Any]) -> tuple[str, Optional[str]]:
    side = p.get("side") if p.get("action") == "TICKET" and p.get("side") in ("CE", "PE") else None
    return ("TICKET" if side else "HOLD"), side


def flip_kind(static_side: Optional[str], shadow_side: Optional[str]) -> Optional[str]:
    if static_side == shadow_side:
        return None
    if static_side and not shadow_side:
        return FLIP_SUPPRESS
    if shadow_side and not static_side:
        return FLIP_NEW
    return FLIP_REVERSE


def _expiry_dates(engine: Any, tick: Any, und: str, ts: int, day: str) -> list[str]:
    try:
        from analysts.shadow import resolve_expiries

        return list(resolve_expiries(engine, tick, und, ts, day)[0])
    except Exception:
        pass
    if und == "NIFTY":
        try:
            from trading_agents_india.index_ce_pe_formulas import default_expiry_tuesdays

            return [str(d) for d in default_expiry_tuesdays()]
        except Exception:
            pass
    return []


@dataclass
class _Session:
    und: str
    day: str
    labeller: RegimeLabeller
    n_fed: int = 0
    label: Optional[dict[str, Any]] = None
    closes: dict[int, float] = field(default_factory=dict)  # completed minute ts -> close
    pending: list[dict[str, Any]] = field(default_factory=list)  # votes waiting for their horizon bar
    minutes_by_primary: dict[str, int] = field(default_factory=dict)


class RegimeShadow:
    """One runner per replay (or one across a multi-day report; each new engine starts new sessions)."""

    def __init__(
        self,
        cfg: Optional[RegimeConfig] = None,
        *,
        root: Optional[Path] = None,
        state: Optional[WeightState] = None,
        sink: Optional[Callable[[str, dict[str, Any]], None]] = None,
        keep_records: bool = False,
    ) -> None:
        from desk_ml.persist import repo_root

        self.cfg = cfg or RegimeConfig()
        self.root = Path(root or repo_root())
        if state is None:
            sp = Path(self.cfg.weights.state_path)
            state = WeightState.load(sp if sp.is_absolute() else self.root / sp, self.cfg.weights)
        self.state = state
        self.sink = sink
        self.keep_records = keep_records
        self.engine: Any = None
        self.sessions: dict[str, _Session] = {}
        self.intermarket: dict[str, dict[str, Any]] = {}
        self.decisions: dict[tuple[str, int], dict[str, Any]] = {}  # (und, ts) -> ticket decision
        self.trade_rec: dict[str, dict[str, Any]] = {}
        self.records: list[dict[str, Any]] = []
        self.days: dict[tuple[str, str], dict[str, Any]] = {}
        self._n_closed_seen = 0
        self._waiting: list[dict[str, Any]] = []  # closed rows whose close is after the current tick
        self._last_ts: dict[str, int] = {}
        # ponytail: replay walks one index at a time (all of NIFTY, then SENSEX from 09:15), so one shared
        # state would show SENSEX at 10:00 NIFTY's 14:00 outcomes. Each index scores into its own copy of
        # the prior-days state; copies merge into `state` at finalize(). Same-day cross-index learning
        # needs a time-merged multi-index walk (same limit as the ledger in event_path).
        self._work: dict[str, WeightState] = {}
        self._to_merge: list[tuple[str, int, str, list[tuple[str, bool]], float]] = []

    # -- engine / session -------------------------------------------------------------------
    def _bind(self, engine: Any) -> None:
        if self.engine is engine:
            return
        if self.engine is not None:
            self.finalize()
        self.engine = engine
        self.sessions = {}
        self.decisions = {}
        self._n_closed_seen = 0
        self._waiting = []
        self._last_ts = {}

    def working_state(self, und: str) -> WeightState:
        if und not in self._work:
            self._work[und] = WeightState.from_dict(self.state.to_dict(), self.cfg.weights)
        return self._work[und]

    def _score(self, und: str, outcome_id: str, ts: int, bucket: str, samples: list[tuple[str, bool]], w: float) -> bool:
        if outcome_id in self.state.applied or not self.working_state(und).apply_outcome(outcome_id, ts, bucket, samples, w):
            return False
        self._to_merge.append((outcome_id, int(ts), bucket, samples, w))
        return True

    def _session(self, engine: Any, step: Any) -> _Session:
        und, ts = str(step.und).upper(), int(step.tick.ts)
        day = datetime.fromtimestamp(ts, IST).date().isoformat()
        sess = self.sessions.get(und)
        if sess is None or sess.day != day:
            sr = (getattr(engine, "sr_levels", None) or {}).get(und) or {}
            sess = _Session(
                und=und, day=day,
                labeller=RegimeLabeller(self.cfg.labels, prior_close=sr.get("pdc"),
                                        expiry_dates=_expiry_dates(engine, step.tick, und, ts, day)),
            )
            self.sessions[und] = sess
            if day not in self.intermarket:
                self.intermarket[day] = regime_for_session(self.root, day, self.cfg.intermarket)
                self._emit("REGIME_LABEL", {"scope": "intermarket", "session_date": day, **self.intermarket[day]})
        return sess

    def _day(self, und: str, day: str) -> dict[str, Any]:
        return self.days.setdefault((day, und), {
            "day": day, "underlying": und, "decisions": 0, "actionable": 0, "static_tickets": 0,
            "shadow_tickets": 0, "flips": {k: 0 for k in FLIP_KINDS}, "flips_actionable": {k: 0 for k in FLIP_KINDS},
            "overlay_vetoes": 0, "outcomes": {"trades": 0, "votes": 0}, "flip_events": [],
        })

    def _emit(self, kind: str, payload: dict[str, Any]) -> None:
        payload = _finite(payload)
        if self.sink is not None:
            self.sink(kind, payload)
        bus = getattr(self.engine, "regime_bus", None) if self.engine is not None else None
        if bus is not None:
            bus.publish(kind, payload, source="regime")

    # -- per tick ---------------------------------------------------------------------------
    def observe(self, engine: Any, step: Any, votes: Sequence[Any], picker: dict[str, Any]) -> dict[str, Any]:
        self._bind(engine)
        und, ts = str(step.und).upper(), int(step.tick.ts)
        if ts < self._last_ts.get(und, ts):
            raise ValueError(f"{und}: tick {ts} before {self._last_ts[und]}")
        self._last_ts[und] = ts
        sess = self._session(engine, step)
        self._feed_bars(sess, list(getattr(step, "bars_1m", None) or []))
        self._scan_trades(engine, ts)

        label = sess.label or {"primary": UNKNOWN, "labels": [UNKNOWN], "version": self.cfg.labels.version}
        bucket = str(label.get(self.cfg.weights.condition_on) or UNKNOWN)
        roster = list(dict.fromkeys(str(v.source) for v in votes if hasattr(v, "source")))
        if self.cfg.weights.enabled:
            weights = self.working_state(und).weights(roster, bucket, ts)
        else:
            weights = {a: self.cfg.weights.static(a) for a in roster}
        shadow = weighted_picker(votes, weights, prev=getattr(step, "older", None),
                                 closed=getattr(step, "closed_1m", None), classified=step.classified)
        _sa, s_side = _decision(picker)
        _wa, w_side = _decision(shadow)
        overlay = overlay_decision(w_side, self.intermarket.get(sess.day), self.cfg.overlay)
        if overlay["veto"]:
            shadow = {**shadow, "side": None, "action": "HOLD", "skip": overlay["reason"],
                      "detail": overlay["reason"], "held_side": w_side}
            w_side = None
        kind = flip_kind(s_side, w_side)
        spoken = {str(v.source): v.side for v in votes if hasattr(v, "spoken") and v.spoken()}
        actionable = not engine.has_working_underlying(und)

        d = self._day(und, sess.day)
        d["decisions"] += 1
        d["actionable"] += int(actionable)
        d["static_tickets"] += int(bool(s_side))
        d["shadow_tickets"] += int(bool(w_side))
        d["overlay_vetoes"] += int(bool(overlay["veto"]))
        rec = {
            "underlying": und, "ts": ts, "day": sess.day, "bucket": bucket, "labels": list(label.get("labels") or []),
            "static": {"side": s_side, "skip": picker.get("skip"), "detail": picker.get("detail")},
            "shadow": {"side": w_side, "skip": shadow.get("skip"), "detail": shadow.get("detail"),
                       "w_ce": shadow.get("w_ce"), "w_pe": shadow.get("w_pe")},
            "overlay": overlay, "flip": kind, "actionable": actionable, "spoken": spoken,
            "weights_version": self.state.version, "mode": self.cfg.mode,
        }
        if kind:
            d["flips"][kind] += 1
            d["flips_actionable"][kind] += int(actionable)
            if actionable:
                d["flip_events"].append(rec)
            log.info("%s %s regime=%s static=%s shadow=%s flip=%s", und, ts, bucket, s_side, w_side, kind)
        if s_side or w_side:
            rec["weights"] = {a: round(w, 4) for a, w in weights.items() if a in spoken}
            self.decisions[(und, ts)] = rec
            self._emit("BOSS_SHADOW", rec)
        if self.keep_records:
            self.records.append(rec)
        if getattr(step, "rolled_1m", False) and spoken and sess.closes:
            m = max(sess.closes)
            sess.pending.append({"id": f"vote:{und}:{m}", "m": m, "ref": sess.closes[m], "bucket": bucket,
                                 "spoken": spoken})
        return shadow if self.cfg.mode == "apply" else picker

    def _feed_bars(self, sess: _Session, bars: list[dict[str, Any]]) -> None:
        done = bars[:-1]  # the last bar is the minute still forming at this tick
        for bar in done[sess.n_fed:]:
            label = sess.labeller.update(bar)
            m, close = int(bar["ts"]), float(bar["close"])
            sess.closes[m] = close
            sess.n_fed += 1
            sess.minutes_by_primary[label["primary"]] = sess.minutes_by_primary.get(label["primary"], 0) + 1
            prev = sess.label
            sess.label = label
            if prev is None or prev["labels"] != label["labels"]:
                log.info("%s regime %s at %s", sess.und, label["labels"], m)
                self._emit("REGIME_LABEL", {"scope": "minute", "underlying": sess.und, **label})
            self._mature_votes(sess, m)

    def _mature_votes(self, sess: _Session, m_now: int) -> None:
        cfg = self.cfg.weights
        horizon = int(cfg.vote_horizon_min) * 60
        keep = []
        for p in sess.pending:
            target = p["m"] + horizon
            if target > m_now:
                keep.append(p)
                continue
            close = sess.closes.get(target)
            if close is None:  # gap in the tape: score on the first completed bar at/after the horizon
                close = sess.closes[m_now]
            move_bps = (close - p["ref"]) / p["ref"] * 1e4
            if abs(move_bps) >= cfg.vote_dead_band_bps and cfg.vote_outcome_weight > 0:
                up = move_bps > 0
                samples = [(a, (side == "CE") == up) for a, side in p["spoken"].items()]
                if self._score(sess.und, p["id"], m_now + 60, p["bucket"], samples, cfg.vote_outcome_weight):
                    self._day(sess.und, sess.day)["outcomes"]["votes"] += 1
        sess.pending = keep

    def _scan_trades(self, engine: Any, now_ts: int) -> None:
        for (_book, u), pos in list((getattr(engine, "opens", None) or {}).items()):
            self._link(str(u).upper(), getattr(pos, "trade_id", None), getattr(pos, "opened_ts", None))
        closed = list(getattr(engine, "closed", None) or [])
        if len(closed) < self._n_closed_seen:
            self._n_closed_seen = 0
        self._waiting.extend(closed[self._n_closed_seen:])
        self._n_closed_seen = len(closed)
        still = []
        for row in self._waiting:
            tid = row.get("trade_id")
            rec = self._link(str(row.get("underlying") or "").upper(), tid, row.get("opened_ts"))
            cts = int(row.get("closed_ts") or 0)
            if cts > now_ts:
                still.append(row)  # not known yet at this tick (another index's later close)
                continue
            net = row.get("realized_pnl_inr")
            if rec is None or not row.get("filled") or net is None:
                continue
            rec["outcome"] = {"trade_id": tid, "net_inr": float(net), "closed_ts": cts}
            samples = [(a, (side == row.get("side")) == (float(net) > 0)) for a, side in rec["spoken"].items()]
            w = self.cfg.weights.trade_outcome_weight
            if float(net) != 0 and w > 0 and self._score(rec["underlying"], f"trade:{tid}", cts, rec["bucket"], samples, w):
                self._day(rec["underlying"], rec["day"])["outcomes"]["trades"] += 1
        self._waiting = still

    def _link(self, und: str, tid: Any, opened_ts: Any) -> Optional[dict[str, Any]]:
        if not tid:
            return None
        rec = self.trade_rec.get(tid)
        if rec is None and opened_ts is not None:
            rec = self.decisions.get((und, int(opened_ts)))
            if rec is not None:
                rec["trade_id"] = tid
                self.trade_rec[tid] = rec
        return rec

    # -- end of replay ----------------------------------------------------------------------
    def finalize(self) -> None:
        """Score trades closed after the last tick (replay end / flatten), then merge every index's
        outcomes into `state` in time order. Call once per replay (the next engine also triggers it)."""
        if self.engine is not None:
            self._scan_trades(self.engine, 2**62)
        for oid, ts, bucket, samples, w in sorted(self._to_merge, key=lambda r: (r[1], r[0])):
            self.state.apply_outcome(oid, ts, bucket, samples, w)
        self._to_merge = []
        self._work = {}

    def day_report(self, day: str, und: str, closed: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """Flip counts and first-order P&L effect for one day/index from the static replay's trades.

        Known effect: a suppressed or reversed static trade removes its net P&L; a kept trade under an
        overlay size multiplier scales it. New or reversed shadow tickets have no fill to price, so they
        are counted as unpriced with an index-points proxy over the vote horizon. Path effects (a
        skipped trade freeing the desk for a later one) are not modelled.
        """
        d = self._day(und, day)
        rows = [r for r in closed if r.get("filled") and str(r.get("underlying")).upper() == und
                and datetime.fromtimestamp(int(r["opened_ts"]), IST).date().isoformat() == day]
        net_static = sum(float(r.get("realized_pnl_inr") or 0.0) for r in rows)
        effect, suppressed, resized = 0.0, 0, 0
        for r in rows:
            rec = self.trade_rec.get(r["trade_id"])
            if rec is None:
                continue
            net = float(r.get("realized_pnl_inr") or 0.0)
            if rec["flip"] in (FLIP_SUPPRESS, FLIP_REVERSE):
                effect -= net
                suppressed += 1
            elif rec["overlay"].get("size_mult", 1.0) != 1.0:
                effect += net * (float(rec["overlay"]["size_mult"]) - 1.0)
                resized += 1
        sess = self.sessions.get(und) if self.sessions.get(und) and self.sessions[und].day == day else None
        horizon = int(self.cfg.weights.vote_horizon_min) * 60
        unpriced, proxy = 0, 0.0
        for ev in d["flip_events"]:
            if ev["flip"] not in (FLIP_NEW, FLIP_REVERSE):
                continue
            unpriced += 1
            if sess is not None and sess.closes:
                m = max((k for k in sess.closes if k <= ev["ts"] - 60), default=None)
                later = [k for k in sess.closes if m is not None and k >= m + horizon]
                if m is not None and later:
                    move = sess.closes[min(later)] - sess.closes[m]
                    proxy += move if ev["shadow"]["side"] == "CE" else -move
        return {
            "day": day, "underlying": und, "decisions": d["decisions"], "actionable": d["actionable"],
            "static_tickets": d["static_tickets"], "shadow_tickets": d["shadow_tickets"],
            "flips": dict(d["flips"]), "flips_actionable": dict(d["flips_actionable"]),
            "overlay_vetoes": d["overlay_vetoes"],
            "trades_static": len(rows), "net_static_inr": round(net_static, 2),
            "trades_flipped": suppressed, "trades_resized": resized,
            "pnl_effect_known_inr": round(effect, 2), "net_hypothetical_known_inr": round(net_static + effect, 2),
            "unpriced_new_tickets": unpriced, "unpriced_proxy_index_points": round(proxy, 2),
            "outcomes_applied": dict(d["outcomes"]),
            "minutes_by_primary": dict(sess.minutes_by_primary) if sess else {},
            "intermarket": {k: (self.intermarket.get(day) or {}).get(k, {}).get("label") for k in ("daily", "weekly")},
            "weights_version": self.state.version,
        }


def jsonl_sink(path: Path) -> Callable[[str, dict[str, Any]], None]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def _write(kind: str, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event_type": kind, **payload}, default=str, allow_nan=False) + "\n")

    return _write
