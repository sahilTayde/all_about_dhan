"""Strategy registry and basket selector for the boss. SHADOW ONLY: logs, never orders.

    config/baskets/<market>.yaml   instruments, selection gates, regime thresholds, strategy cards
    data/lab/basket_<market>.json  lab refresh (optional, gitignored); its cards replace yaml cards by id
    data/shadow/basket/<day>.jsonl one row per selection (pre_open, then each regime change)

The boss calls `BasketShadow.on_tick` before its entry decision. The selector reads regime labels
built only from data available before that decision (prior sessions, closed 1m bars of today) and
returns ranked weights. Weights are written to the shadow log and nothing else reads them.
Off by default (`basket_selector.enabled` in config/event_path.yaml or env USE_BASKET_SELECTOR=1);
the founder file `basket_selector.founder_off_file` switches it off entirely. Schema: docs/baskets.md.

    python -m boss.basket validate data/lab/basket_india.json   # lab: check a file before shipping it
    python -m boss.basket off | on | status                     # founder control
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import yaml

from analysts.shadow import efficiency_ratio, log_returns, realised_vol_pct

log = logging.getLogger("boss.basket")
IST = timezone(timedelta(hours=5, minutes=30))
ENV_FLAG = "USE_BASKET_SELECTOR"
LAB_SCHEMA_VERSION = 1
STATUSES = ("active_candidate", "watch", "parked", "parked_for_forex_test")
SOURCES = ("trader", "paper")
RULE_KEYS = ("entry", "exit", "strike", "sizing", "skip")
TRENDS, VOLS, EXPIRIES = ("trend", "chop"), ("high_vol", "low_vol"), ("expiry", "non_expiry")
REGIME_KEYS = tuple(f"{t}.{v}.{e}" for t in TRENDS for v in VOLS for e in EXPIRIES)
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
UNKNOWN = "unknown"
CARD_KEYS = {"id", "source", "markets", "adaptations", "rules", "param_ranges", "scores", "notes"}
SCORE_KEYS = ("net_pnl", "pf", "trades", "win_rate", "dsr", "weight", "rank", "status")
SELECTION_KEYS = {"max_total_weight", "min_trades", "min_pf", "min_dsr", "require_positive_net"}
REGIME_CFG_KEYS = {"preopen_days", "preopen_trend_er_min", "preopen_high_vol_pct",
                   "intraday_bars", "intraday_trend_er_min", "intraday_high_vol_pct"}
_ID = re.compile(r"^[A-Z][A-Z0-9_.-]{1,63}$")


class BasketError(ValueError):
    """A basket, card or lab file that does not match docs/baskets.md."""


@dataclass(frozen=True)
class RegimeScore:
    net_pnl: float
    pf: float
    trades: int
    win_rate: float
    dsr: float
    weight: float
    rank: int
    status: str


@dataclass(frozen=True)
class StrategyCard:
    id: str
    source: dict
    markets: tuple
    adaptations: dict
    rules: dict
    param_ranges: dict
    scores: dict  # regime key -> RegimeScore
    notes: str = ""


@dataclass(frozen=True)
class Instrument:
    symbol: str
    exchange: Optional[str]
    lot_size: Optional[int]
    expiry_weekday: Optional[str]
    session: dict
    tick_size: Optional[float]


@dataclass(frozen=True)
class Basket:
    market: str
    activatable: bool
    instruments: dict  # symbol -> Instrument
    selection: dict
    regime: dict
    lab_scores: Optional[str]
    cards: dict  # id -> StrategyCard
    path: str = ""


# ------------------------------------------------------------------ validation


def _map(raw: Any, where: str) -> dict:
    if not isinstance(raw, dict):
        raise BasketError(f"{where}: expected a mapping")
    return raw


def _number(raw: Any, where: str, *, lo: Optional[float] = None, hi: Optional[float] = None, integer: bool = False) -> Any:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or (integer and not isinstance(raw, int)):
        raise BasketError(f"{where}: expected {'an integer' if integer else 'a number'}, got {raw!r}")
    if not math.isfinite(float(raw)):
        raise BasketError(f"{where}: must be finite")
    if (lo is not None and raw < lo) or (hi is not None and raw > hi):
        raise BasketError(f"{where}: {raw} outside [{lo}, {hi}]")
    return int(raw) if integer else float(raw)


def _no_extra(raw: dict, allowed: set, where: str) -> None:
    extra = sorted(set(raw) - allowed)
    if extra:
        raise BasketError(f"{where}: unknown keys {extra}")


def parse_score(raw: Any, where: str) -> RegimeScore:
    d = _map(raw, where)
    missing = [k for k in SCORE_KEYS if k not in d]
    if missing:
        raise BasketError(f"{where}: unscored, missing {missing}")
    _no_extra(d, set(SCORE_KEYS), where)
    if d["status"] not in STATUSES:
        raise BasketError(f"{where}.status: {d['status']!r} not in {list(STATUSES)}")
    return RegimeScore(
        net_pnl=_number(d["net_pnl"], f"{where}.net_pnl"),
        pf=_number(d["pf"], f"{where}.pf", lo=0),
        trades=_number(d["trades"], f"{where}.trades", lo=0, integer=True),
        win_rate=_number(d["win_rate"], f"{where}.win_rate", lo=0, hi=1),
        dsr=_number(d["dsr"], f"{where}.dsr", lo=0, hi=1),
        weight=_number(d["weight"], f"{where}.weight", lo=0),
        rank=_number(d["rank"], f"{where}.rank", lo=1, integer=True),
        status=str(d["status"]),
    )


def parse_card(raw: Any, *, require_scores: bool, where: str = "card") -> StrategyCard:
    d = _map(raw, where)
    _no_extra(d, CARD_KEYS, where)
    cid = d.get("id")
    if not isinstance(cid, str) or not _ID.match(cid):
        raise BasketError(f"{where}.id: {cid!r} must match {_ID.pattern}")
    where = f"{where} {cid}"
    src = _map(d.get("source"), f"{where}.source")
    if src.get("kind") not in SOURCES or not str(src.get("ref") or "").strip():
        raise BasketError(f"{where}.source: need kind in {list(SOURCES)} and a non-empty ref")
    markets = d.get("markets")
    if not isinstance(markets, list) or not markets or not all(isinstance(m, str) and m for m in markets):
        raise BasketError(f"{where}.markets: need a non-empty list of underlyings")
    markets = tuple(m.upper() for m in markets)
    adaptations = _map(d.get("adaptations", {}), f"{where}.adaptations")
    for und, params in adaptations.items():
        if str(und).upper() not in markets:
            raise BasketError(f"{where}.adaptations: {und} is not in markets")
        _map(params, f"{where}.adaptations.{und}")
    rules = _map(d.get("rules"), f"{where}.rules")
    if sorted(rules) != sorted(RULE_KEYS):
        raise BasketError(f"{where}.rules: need exactly {list(RULE_KEYS)}")
    for k in RULE_KEYS:
        if not _map(rules[k], f"{where}.rules.{k}"):
            raise BasketError(f"{where}.rules.{k}: empty; give the exact parameters")
    ranges = _map(d.get("param_ranges"), f"{where}.param_ranges")
    for name, vals in ranges.items():
        if not isinstance(vals, list) or not vals or not all(isinstance(v, (int, float, str, bool)) for v in vals):
            raise BasketError(f"{where}.param_ranges.{name}: need a non-empty list of tested values")
    scores_raw = _map(d.get("scores", {}), f"{where}.scores")
    if require_scores and not scores_raw:
        raise BasketError(f"{where}: unscored (no regime scores)")
    scores = {}
    for key, sc in scores_raw.items():
        if key not in REGIME_KEYS:
            raise BasketError(f"{where}.scores: {key!r} is not a regime key {list(REGIME_KEYS)}")
        scores[key] = parse_score(sc, f"{where}.scores.{key}")
    return StrategyCard(id=cid, source=dict(src), markets=markets, adaptations=dict(adaptations), rules=dict(rules),
                        param_ranges=dict(ranges), scores=scores, notes=str(d.get("notes") or ""))


def _instrument(sym: str, raw: Any) -> Instrument:
    d = _map(raw, f"instruments.{sym}")
    wd = d.get("expiry_weekday")
    if wd is not None and wd not in WEEKDAYS:
        raise BasketError(f"instruments.{sym}.expiry_weekday: {wd!r} not in {list(WEEKDAYS)} or null")
    lot, tick = d.get("lot_size"), d.get("tick_size")
    return Instrument(
        symbol=sym, exchange=d.get("exchange"),
        lot_size=None if lot is None else _number(lot, f"instruments.{sym}.lot_size", lo=1, integer=True),
        expiry_weekday=wd, session=dict(_map(d.get("session") or {}, f"instruments.{sym}.session")),
        tick_size=None if tick is None else _number(tick, f"instruments.{sym}.tick_size", lo=0),
    )


def load_basket(path: Path) -> Basket:
    path = Path(path)
    d = _map(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    market = d.get("market")
    if not isinstance(market, str) or not market:
        raise BasketError(f"{path}: market is required")
    if not isinstance(d.get("activatable"), bool):
        raise BasketError(f"{path}: activatable must be true or false")
    instruments = {str(s).upper(): _instrument(str(s).upper(), v) for s, v in _map(d.get("instruments"), "instruments").items()}
    sel = _map(d.get("selection"), "selection")
    _no_extra(sel, SELECTION_KEYS, "selection")
    selection = {
        "max_total_weight": _number(sel.get("max_total_weight"), "selection.max_total_weight", lo=0),
        "min_trades": _number(sel.get("min_trades"), "selection.min_trades", lo=0, integer=True),
        "min_pf": _number(sel.get("min_pf"), "selection.min_pf", lo=0),
        "min_dsr": _number(sel.get("min_dsr"), "selection.min_dsr", lo=0, hi=1),
        "require_positive_net": bool(sel.get("require_positive_net", True)),
    }
    reg = _map(d.get("regime"), "regime")
    _no_extra(reg, REGIME_CFG_KEYS, "regime")
    regime = {k: _number(reg.get(k), f"regime.{k}", lo=0, integer=k.endswith(("_days", "_bars"))) for k in sorted(REGIME_CFG_KEYS)}
    cards: dict[str, StrategyCard] = {}
    for n, raw in enumerate(d.get("strategies") or []):
        card = parse_card(raw, require_scores=False, where=f"{path.name} strategies[{n}]")
        if card.id in cards:
            raise BasketError(f"{path}: duplicate strategy id {card.id}")
        _check_markets(card, instruments)
        cards[card.id] = card
    return Basket(market=market, activatable=d["activatable"], instruments=instruments, selection=selection,
                  regime=regime, lab_scores=d.get("lab_scores"), cards=cards, path=str(path))


def _check_markets(card: StrategyCard, instruments: dict) -> None:
    unknown = [m for m in card.markets if m not in instruments]
    if unknown:
        raise BasketError(f"card {card.id}: markets {unknown} are not instruments of this basket")


def load_lab_basket(path: Path, basket: Basket) -> tuple[dict, list]:
    """(valid cards by id, rejected entries). A malformed file raises BasketError; bad entries are rejected one by one."""
    try:
        blob = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except (OSError, ValueError) as exc:
        raise BasketError(f"{path}: unreadable lab file ({exc})") from exc
    d = _map(blob, str(path))
    if d.get("schema_version") != LAB_SCHEMA_VERSION:
        raise BasketError(f"{path}: schema_version must be {LAB_SCHEMA_VERSION}")
    if d.get("market") != basket.market:
        raise BasketError(f"{path}: market {d.get('market')!r} is not {basket.market!r}")
    for k in ("generated_at", "source"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            raise BasketError(f"{path}: {k} is required")
    if not isinstance(d.get("strategies"), list):
        raise BasketError(f"{path}: strategies must be a list")
    cards: dict[str, StrategyCard] = {}
    rejected: list[dict[str, Any]] = []
    for n, raw in enumerate(d["strategies"]):
        rid = raw.get("id") if isinstance(raw, dict) else None
        try:
            card = parse_card(raw, require_scores=True, where=f"strategies[{n}]")
            _check_markets(card, basket.instruments)
            if card.id in cards:
                raise BasketError(f"strategies[{n}]: duplicate id {card.id}")
        except BasketError as exc:
            rejected.append({"index": n, "id": rid, "reason": str(exc)})
            continue
        cards[card.id] = card
    return cards, rejected


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not allowed (cap pf / weights before writing)")


def with_lab(basket: Basket, root: Path) -> tuple[Basket, dict[str, Any]]:
    """Basket with lab cards merged in (lab wins by id). A broken lab file is ignored as a whole and reported."""
    meta: dict[str, Any] = {"path": basket.lab_scores, "found": False, "loaded": [], "rejected": [], "error": None}
    if not basket.lab_scores:
        return basket, meta
    path = Path(basket.lab_scores)
    path = path if path.is_absolute() else Path(root) / path
    if not path.is_file():
        return basket, meta
    meta["found"] = True
    try:
        cards, meta["rejected"] = load_lab_basket(path, basket)
    except BasketError as exc:
        meta["error"] = str(exc)
        log.warning("lab basket rejected: %s", exc)
        return basket, meta
    meta["loaded"] = sorted(cards)
    return replace(basket, cards={**basket.cards, **cards}), meta


# ------------------------------------------------------------------ regime labels (pre-entry only)


def ist_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), IST).date().isoformat()


def expiry_label(session_date: str, inst: Instrument) -> str:
    if inst.expiry_weekday is None:
        return UNKNOWN
    return "expiry" if WEEKDAYS[date.fromisoformat(session_date).weekday()] == inst.expiry_weekday else "non_expiry"


def _labels(closes: Sequence[float], er_min: float, vol_pct: Optional[float], vol_min: float) -> tuple[str, str, dict]:
    er = efficiency_ratio(closes)
    trend = UNKNOWN if er is None else ("trend" if er >= er_min else "chop")
    vol = UNKNOWN if vol_pct is None else ("high_vol" if vol_pct >= vol_min else "low_vol")
    return trend, vol, {"er": None if er is None else round(er, 6), "vol_pct": None if vol_pct is None else round(vol_pct, 6)}


def preopen_regime(prior_daily: Sequence[dict], session_date: str, inst: Instrument, cfg: dict) -> dict[str, Any]:
    """Labels from prior sessions only: any daily row dated today or later is dropped."""
    n = int(cfg["preopen_days"])
    rows = [r for r in prior_daily if str(r.get("date", ""))[:10] < session_date][-(n + 1):]
    closes = [float(r["close"]) for r in rows]
    vol_pct = None
    if len(closes) < n + 1:
        closes = []
    else:
        rets = log_returns(closes) or []
        if len(rets) >= 2:
            mean = sum(rets) / len(rets)
            vol_pct = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(252) * 100.0
    trend, vol, inputs = _labels(closes, cfg["preopen_trend_er_min"], vol_pct, cfg["preopen_high_vol_pct"])
    inputs.update(n_days=len(closes), last_day=str(rows[-1].get("date"))[:10] if closes else None)
    return _regime(trend, vol, expiry_label(session_date, inst), "pre_open", inputs)


def intraday_regime(bars_1m: Sequence[dict], now_ts: int, session_date: str, inst: Instrument, cfg: dict) -> dict[str, Any]:
    """Labels from today's 1m bars that closed at or before ``now_ts``; the forming minute is never used."""
    n = int(cfg["intraday_bars"])
    closed = [b for b in bars_1m if int(b["ts"]) + 60 <= int(now_ts) and ist_date(int(b["ts"])) == session_date]
    closes = [float(b["close"]) for b in closed][-(n + 1):]
    if len(closes) < n + 1:
        return _regime(UNKNOWN, UNKNOWN, expiry_label(session_date, inst), "intraday", {"n_bars": len(closed)})
    rets = log_returns(closes)
    trend, vol, inputs = _labels(closes, cfg["intraday_trend_er_min"], realised_vol_pct(rets) if rets else None,
                                 cfg["intraday_high_vol_pct"])
    inputs.update(n_bars=len(closed), last_bar_ts=int(closed[-1]["ts"]))
    return _regime(trend, vol, expiry_label(session_date, inst), "intraday", inputs)


def _regime(trend: str, vol: str, expiry: str, source: str, inputs: dict) -> dict[str, Any]:
    key = f"{trend}.{vol}.{expiry}"
    return {"trend": trend, "vol": vol, "expiry": expiry, "key": key if key in REGIME_KEYS else None,
            "source": source, "inputs": inputs}


def combine(pre: dict[str, Any], intra: dict[str, Any]) -> dict[str, Any]:
    """Intraday labels replace pre-open ones per dimension once they are known."""
    trend = intra["trend"] if intra["trend"] != UNKNOWN else pre["trend"]
    vol = intra["vol"] if intra["vol"] != UNKNOWN else pre["vol"]
    src = "intraday" if (intra["trend"], intra["vol"]) != (UNKNOWN, UNKNOWN) else "pre_open"
    return _regime(trend, vol, pre["expiry"], src, {"pre_open": pre["inputs"], "intraday": intra["inputs"]})


# ------------------------------------------------------------------ selector (pure, deterministic)


def _gate(sc: Optional[RegimeScore], sel: dict) -> Optional[str]:
    if sc is None:
        return "unscored_regime"
    if sc.status != "active_candidate":
        return f"status_{sc.status}"
    if sc.trades < sel["min_trades"]:
        return "failed_min_trades"
    if sc.pf < sel["min_pf"]:
        return "failed_pf"
    if sel["require_positive_net"] and sc.net_pnl <= 0:
        return "failed_net_pnl"
    if sc.dsr < sel["min_dsr"]:
        return "failed_dsr"
    if sc.weight <= 0:
        return "zero_weight"
    return None


def select_basket(basket: Basket, underlying: str, regime: dict[str, Any]) -> dict[str, Any]:
    """Ranked, weighted strategies for ``underlying`` in ``regime``. Failed / parked / unscored = weight 0."""
    und, key, sel = underlying.upper(), regime.get("key"), basket.selection
    rows = []
    for cid in sorted(basket.cards):
        card = basket.cards[cid]
        if und not in card.markets:
            continue
        sc = card.scores.get(key) if key else None
        if not basket.activatable:
            reason = "basket_parked"
        elif key is None:
            reason = "regime_unknown"
        else:
            reason = _gate(sc, sel)
        rows.append({"id": cid, "raw_weight": sc.weight if reason is None else 0.0, "reason": reason or "selected",
                     "score": asdict(sc) if sc else None, "_rank": sc.rank if sc else 0})
    total = sum(r["raw_weight"] for r in rows)
    cap = sel["max_total_weight"]
    scale = min(1.0, cap / total) if total > 0 else 1.0
    live = sorted((r for r in rows if r["raw_weight"] > 0), key=lambda r: (r["_rank"], -r["raw_weight"], r["id"]))
    dead = [r for r in rows if r["raw_weight"] <= 0]
    out = []
    for n, r in enumerate(live + dead, start=1):
        r.pop("_rank")
        # Round down to 1e-6 so the sum never exceeds the cap (inner round strips float fuzz: 0.3 stays 0.3).
        weight = math.floor(round(r["raw_weight"] * scale * 1e6, 6)) / 1e6
        out.append({**r, "weight": weight, "rank": n if r["raw_weight"] > 0 else None})
    return {
        "market": basket.market, "underlying": und, "regime_key": key, "active": bool(live) and basket.activatable,
        "total_weight": round(sum(r["weight"] for r in out), 6), "cap": cap, "scaled": scale < 1.0, "strategies": out,
    }


# ------------------------------------------------------------------ boss hook + shadow log


class BasketShadow:
    """What the boss holds when the feature is on. Writes rows; returns them for tests. Never orders."""

    def __init__(self, baskets: Sequence[Basket], *, out_dir: Path, founder_off_file: Optional[Path] = None,
                 lab: Optional[dict[str, dict]] = None) -> None:
        self.baskets = list(baskets)
        self.by_und: dict[str, Basket] = {}
        for b in self.baskets:
            if not b.activatable:
                continue  # parked markets (forex) load and validate but never attach
            for sym in sorted(b.instruments):
                self.by_und.setdefault(sym, b)
        self.out_dir = Path(out_dir)
        self.founder_off_file = Path(founder_off_file) if founder_off_file else None
        self.lab = dict(lab or {})
        self.rows: list[dict[str, Any]] = []
        self._pre: dict[tuple[str, str], dict] = {}
        self._last: dict[tuple[str, str], tuple] = {}
        self._n_closed: dict[tuple[str, str], int] = {}
        self._seen: dict[Path, set] = {}

    def founder_off(self) -> bool:
        return self.founder_off_file is not None and self.founder_off_file.exists()

    def on_tick(self, underlying: str, now_ts: int, bars_1m: Sequence[dict], prior_daily: Sequence[dict]) -> Optional[dict]:
        und = underlying.upper()
        basket = self.by_und.get(und)
        if basket is None or self.founder_off():
            return None
        day = ist_date(now_ts)
        k = (und, day)
        inst = basket.instruments[und]
        if k not in self._pre:
            self._pre[k] = preopen_regime(prior_daily, day, inst, basket.regime)
            return self._emit(basket, und, now_ts, day, self._pre[k], "pre_open")
        n_closed = sum(1 for b in bars_1m if int(b["ts"]) + 60 <= int(now_ts))
        if self._n_closed.get(k) == n_closed:
            return None  # labels only move when a minute closes
        self._n_closed[k] = n_closed
        reg = combine(self._pre[k], intraday_regime(bars_1m, now_ts, day, inst, basket.regime))
        if (reg["trend"], reg["vol"], reg["expiry"]) == self._last.get(k):
            return None
        return self._emit(basket, und, now_ts, day, reg, "regime_change")

    def _emit(self, basket: Basket, und: str, ts: int, day: str, reg: dict, trigger: str) -> dict:
        self._last[(und, day)] = (reg["trend"], reg["vol"], reg["expiry"])
        row = {
            "day": day, "ts": int(ts), "time_ist": datetime.fromtimestamp(int(ts), IST).isoformat(timespec="seconds"),
            "underlying": und, "market": basket.market, "trigger": trigger, "regime": reg,
            "basket": select_basket(basket, und, reg), "lab": self.lab.get(basket.market),
            "shadow": True, "places_orders": False,
        }
        self.rows.append(row)
        self._write(day, row)
        return row

    def _write(self, day: str, row: dict) -> None:
        path = self.out_dir / f"{day}.jsonl"
        line = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
        seen = self._seen.get(path)
        if seen is None:  # the live loop re-replays the session: never append the same row twice
            seen = set(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else set()
            self._seen[path] = seen
        if line in seen:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        seen.add(line)

    def summary(self) -> dict[str, Any]:
        return {"rows": len(self.rows), "underlyings": sorted(self.by_und), "out_dir": str(self.out_dir),
                "lab": self.lab}


def enabled(settings: dict[str, Any]) -> bool:
    env = os.environ.get(ENV_FLAG, "").strip().lower()
    if env:
        return env in {"1", "true", "yes", "on"}
    return bool((settings.get("basket_selector") or {}).get("enabled", False))


def shadow_from_settings(settings: dict[str, Any], *, root: Path) -> Optional[BasketShadow]:
    """None unless the feature is on and the founder has not switched it off. Bad config = off, logged."""
    if not enabled(settings):
        return None
    cfg = settings.get("basket_selector") or {}
    root = Path(root)
    founder = root / str(cfg.get("founder_off_file") or "data/founder/basket_selector_off")
    if founder.exists():
        log.info("basket selector: founder switched it off (%s)", founder)
        return None
    baskets, lab = [], {}
    try:
        for rel in cfg.get("baskets") or ["config/baskets/india.yaml"]:
            b, meta = with_lab(load_basket(root / rel), root)
            baskets.append(b)
            lab[b.market] = meta
    except (OSError, BasketError, yaml.YAMLError) as exc:
        log.error("basket selector off: %s", exc)
        return None
    return BasketShadow(baskets, out_dir=root / str(cfg.get("out_dir") or "data/shadow/basket"),
                        founder_off_file=founder, lab=lab)


# ----------------------------------------------------------------------- CLI


def main(argv: Optional[Sequence[str]] = None) -> int:
    from desk_ml.persist import repo_root

    ap = argparse.ArgumentParser(prog="python -m boss.basket", description="Strategy basket: validate lab output, founder on/off.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a lab basket JSON against its config/baskets/<market>.yaml")
    v.add_argument("path", type=Path)
    for name in ("off", "on", "status"):
        sub.add_parser(name, help=f"founder control: {name}")
    args = ap.parse_args(argv)
    root = repo_root()
    settings = yaml.safe_load((root / "config" / "event_path.yaml").read_text(encoding="utf-8")) or {}
    founder = root / str((settings.get("basket_selector") or {}).get("founder_off_file") or "data/founder/basket_selector_off")
    if args.cmd == "validate":
        try:
            market = json.loads(args.path.read_text(encoding="utf-8")).get("market")
            cards, rejected = load_lab_basket(args.path, load_basket(root / "config" / "baskets" / f"{market}.yaml"))
        except (OSError, ValueError, AttributeError) as exc:
            print(f"REJECTED file: {exc}")
            return 1
        print(json.dumps({"accepted": sorted(cards), "rejected": rejected}, indent=2))
        return 1 if rejected else 0
    if args.cmd == "off":
        founder.parent.mkdir(parents=True, exist_ok=True)
        founder.write_text("basket selector switched off by founder\n", encoding="utf-8")
    elif args.cmd == "on" and founder.exists():
        founder.unlink()
    print(json.dumps({"enabled_flag": enabled(settings), "founder_off": founder.exists(), "founder_off_file": str(founder)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
