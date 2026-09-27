"""Strategy registry and basket selector for the boss. SHADOW ONLY: logs, never orders.

    config/baskets/<market>.yaml   instruments, selection gates, strategy cards
    config/baskets/selector.yaml   flags: enabled (default false), founder off file, paths
    data/shadow/basket/lab/basket_<market>.json  lab refresh (optional, gitignored); cards replace yaml cards by id
    data/shadow/basket/<day>.jsonl one row per selection (pre_open, then each regime change)

Regime labels are not computed here: they are the regime service's (`desk_ml.regime`, PR #21)
minute labels, built from completed 1m bars only. `pre_open` runs on an index's first tick, before
the boss's first decision (only the expiry flag is known; the labeller is still warming up), and
`on_label` runs for every minute REGIME_LABEL the regime service publishes. A lab file scored on data
from the session day or later is ignored for that session (same rule as the regime weight state).
Weights are written to the shadow log and nothing else reads them.
Off by default (`enabled` in config/baskets/selector.yaml or env USE_BASKET_SELECTOR=1); the founder
file `founder_off_file` switches it off entirely. It hooks into the event bus (MARKET_TICK, REGIME_LABEL)
without touching boss code; the one-line integration point and the schema are in docs/baskets.md.

    python -m strategy_basket validate data/shadow/basket/lab/basket_india.json   # lab: check a file before shipping it
    python -m strategy_basket off | on | status                     # founder control
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import yaml

from desk_ml.regime.labels import (
    EXPIRY_DAY, IST, PRIMARY_LABELS, UNKNOWN, VOL_COMPRESSION, VOL_EXPANSION,
)

log = logging.getLogger("boss.basket")
ENV_FLAG = "USE_BASKET_SELECTOR"
LAB_SCHEMA_VERSION = 1
STATUSES = ("active_candidate", "watch", "parked", "parked_for_forex_test")
SOURCES = ("trader", "paper")
RULE_KEYS = ("entry", "exit", "strike", "sizing", "skip")
# The regime service labels vol only when it expands or compresses; neither (including warm-up) = vol_normal.
VOL_NORMAL, NON_EXPIRY_DAY = "vol_normal", "non_expiry_day"
VOLS, EXPIRIES = (VOL_EXPANSION, VOL_COMPRESSION, VOL_NORMAL), (EXPIRY_DAY, NON_EXPIRY_DAY)
REGIME_KEYS = tuple(f"{p}.{v}.{e}" for p in PRIMARY_LABELS for v in VOLS for e in EXPIRIES)
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
CARD_KEYS = {"id", "source", "markets", "adaptations", "rules", "param_ranges", "scores", "notes"}
SCORE_KEYS = ("net_pnl", "pf", "trades", "win_rate", "dsr", "weight", "rank", "status")
SELECTION_KEYS = {"max_total_weight", "min_trades", "min_pf", "min_dsr", "require_positive_net"}
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
    if "regime" in d:
        raise BasketError(f"{path}: regime thresholds live in config/regime.yaml (desk_ml.regime labels), not here")
    cards: dict[str, StrategyCard] = {}
    for n, raw in enumerate(d.get("strategies") or []):
        card = parse_card(raw, require_scores=False, where=f"{path.name} strategies[{n}]")
        if card.id in cards:
            raise BasketError(f"{path}: duplicate strategy id {card.id}")
        _check_markets(card, instruments)
        cards[card.id] = card
    return Basket(market=market, activatable=d["activatable"], instruments=instruments, selection=selection,
                  lab_scores=d.get("lab_scores"), cards=cards, path=str(path))


def _check_markets(card: StrategyCard, instruments: dict) -> None:
    unknown = [m for m in card.markets if m not in instruments]
    if unknown:
        raise BasketError(f"card {card.id}: markets {unknown} are not instruments of this basket")


def load_lab_basket(path: Path, basket: Basket) -> tuple[dict, list, str]:
    """(valid cards by id, rejected entries, data_until). A malformed file raises BasketError; bad entries
    are rejected one by one."""
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
    try:
        data_until = date.fromisoformat(str(d.get("data_until"))).isoformat()
    except ValueError:
        raise BasketError(f"{path}: data_until (last session date the scores used, YYYY-MM-DD) is required") from None
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
    return cards, rejected, data_until


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not allowed (cap pf / weights before writing)")


def load_lab(basket: Basket, root: Path) -> tuple[dict, dict[str, Any]]:
    """(lab cards by id, meta). A broken lab file is ignored as a whole and reported in meta."""
    meta: dict[str, Any] = {"path": basket.lab_scores, "found": False, "loaded": [], "rejected": [],
                            "data_until": None, "error": None}
    if not basket.lab_scores:
        return {}, meta
    path = Path(basket.lab_scores)
    path = path if path.is_absolute() else Path(root) / path
    if not path.is_file():
        return {}, meta
    meta["found"] = True
    try:
        cards, meta["rejected"], meta["data_until"] = load_lab_basket(path, basket)
    except BasketError as exc:
        meta["error"] = str(exc)
        log.warning("lab basket rejected: %s", exc)
        return {}, meta
    meta["loaded"] = sorted(cards)
    return cards, meta


def for_session(basket: Basket, lab_cards: dict, meta: dict[str, Any], day: str) -> tuple[Basket, dict[str, Any]]:
    """Lab cards merged in (lab wins by id) only when their scores end before ``day``.

    Scores that used the session day or later would leak the future into the selection, so the file
    is ignored for that session (same rule as the regime service's saved weight state).
    """
    if not lab_cards:
        return basket, {**meta, "used": False}
    if meta["data_until"] >= day:
        log.warning("lab basket %s scored through %s, on or after session %s; ignored for this session",
                    meta["path"], meta["data_until"], day)
        return basket, {**meta, "used": False, "ignored": f"data_until {meta['data_until']} is not before {day}"}
    return replace(basket, cards={**basket.cards, **lab_cards}), {**meta, "used": True}


# ------------------------------------------------------------------ regime (the regime service's labels)


def ist_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), IST).date().isoformat()


def regime_from_label(label: Mapping[str, Any], *, source: str = "regime_service") -> dict[str, Any]:
    """Basket regime key from a `desk_ml.regime` minute label (the REGIME_LABEL scope=minute payload)."""
    primary = label.get("primary") if label.get("primary") in PRIMARY_LABELS else UNKNOWN
    vol = label.get("vol") if label.get("vol") in (VOL_EXPANSION, VOL_COMPRESSION) else VOL_NORMAL
    expiry = EXPIRY_DAY if label.get("expiry_day") else NON_EXPIRY_DAY
    return {"primary": primary, "vol": vol, "expiry": expiry, "key": f"{primary}.{vol}.{expiry}",
            "source": source, "label_ts": label.get("ts"), "labels": list(label.get("labels") or []),
            "version": label.get("version"), "features": dict(label.get("features") or {})}


def preopen_regime(expiry_day: bool, version: Optional[str] = None) -> dict[str, Any]:
    """Before the first completed bar the labeller is warming up: primary unknown, only the expiry flag is known."""
    labels = [UNKNOWN] + ([EXPIRY_DAY] if expiry_day else [])
    return regime_from_label({"primary": UNKNOWN, "vol": None, "expiry_day": expiry_day, "labels": labels,
                              "version": version}, source="pre_open")


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
                 labs: Optional[dict[str, tuple[dict, dict]]] = None) -> None:
        self.baskets = list(baskets)
        self.by_und: dict[str, Basket] = {}
        for b in self.baskets:
            if not b.activatable:
                continue  # parked markets (forex) load and validate but never attach
            for sym in sorted(b.instruments):
                self.by_und.setdefault(sym, b)
        self.out_dir = Path(out_dir)
        self.founder_off_file = Path(founder_off_file) if founder_off_file else None
        self.labs = dict(labs or {})  # market -> (lab cards, load_lab meta)
        self.rows: list[dict[str, Any]] = []
        self.labels_seen = 0
        self._last: dict[tuple[str, str], str] = {}  # (underlying, day) -> regime key last logged
        self._seen: dict[Path, set] = {}

    def founder_off(self) -> bool:
        return self.founder_off_file is not None and self.founder_off_file.exists()

    def _basket(self, und: str) -> Optional[Basket]:
        basket = self.by_und.get(und)
        return None if basket is None or self.founder_off() else basket

    def pre_open(self, underlying: str, now_ts: int, *, expiry_day: bool, version: Optional[str] = None) -> Optional[dict]:
        """Once per index and day, before its first decision."""
        und = underlying.upper()
        basket = self._basket(und)
        day = ist_date(now_ts)
        if basket is None or (und, day) in self._last:
            return None
        return self._emit(basket, und, now_ts, day, preopen_regime(expiry_day, version), "pre_open")

    def on_label(self, label: Mapping[str, Any], now_ts: int) -> Optional[dict]:
        """A regime-service REGIME_LABEL payload seen at tick ``now_ts``. Minute labels only."""
        if label.get("scope") != "minute":
            return None
        und = str(label.get("underlying") or "").upper()
        basket = self._basket(und)
        if basket is None:
            return None
        lts = int(label["ts"])
        if lts + 60 > int(now_ts):  # the labelled minute must have closed by the time the boss sees it
            raise ValueError(f"{und}: label for minute {lts} is not complete at tick {now_ts}")
        self.labels_seen += 1
        day = ist_date(lts)
        reg = regime_from_label(label)
        if self._last.get((und, day)) == reg["key"]:
            return None  # the label list moved (e.g. gap_day) but the basket key did not
        return self._emit(basket, und, now_ts, day, reg, "regime_change")

    def _emit(self, basket: Basket, und: str, ts: int, day: str, reg: dict, trigger: str) -> dict:
        self._last[(und, day)] = reg["key"]
        lab = None
        if basket.market in self.labs:
            cards, meta = self.labs[basket.market]
            basket, lab = for_session(basket, cards, meta, day)
        row = {
            "day": day, "ts": int(ts), "time_ist": datetime.fromtimestamp(int(ts), IST).isoformat(timespec="seconds"),
            "underlying": und, "market": basket.market, "trigger": trigger, "regime": reg,
            "basket": select_basket(basket, und, reg), "lab": lab, "shadow": True, "places_orders": False,
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
        return {"rows": len(self.rows), "labels_seen": self.labels_seen, "underlyings": sorted(self.by_und),
                "out_dir": str(self.out_dir), "lab": {m: meta for m, (_c, meta) in sorted(self.labs.items())}}


SETTINGS_PATH = Path("config") / "baskets" / "selector.yaml"
DEFAULT_FOUNDER_OFF = "data/shadow/basket/FOUNDER_OFF"


def load_settings(root: Optional[Path] = None) -> dict[str, Any]:
    """`config/baskets/selector.yaml`; a missing file means off."""
    from desk_ml.persist import repo_root

    path = Path(root or repo_root()) / SETTINGS_PATH
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def enabled(settings: Mapping[str, Any]) -> bool:
    env = os.environ.get(ENV_FLAG, "").strip().lower()
    if env:
        return env in {"1", "true", "yes", "on"}
    return settings.get("enabled", False) is True


def founder_off_path(settings: Mapping[str, Any], root: Path) -> Path:
    return Path(root) / str(settings.get("founder_off_file") or DEFAULT_FOUNDER_OFF)


def shadow_from_settings(settings: Mapping[str, Any], *, root: Path) -> Optional[BasketShadow]:
    """None unless the feature is on and the founder has not switched it off. Bad config = off, logged."""
    if not enabled(settings):
        return None
    root = Path(root)
    founder = founder_off_path(settings, root)
    if founder.exists():
        log.info("basket selector: founder switched it off (%s)", founder)
        return None
    try:
        return build_shadow(settings, root=root)
    except (OSError, BasketError, yaml.YAMLError) as exc:
        log.error("basket selector off: %s", exc)
        return None


def build_shadow(settings: Mapping[str, Any], *, root: Path, out_dir: Optional[Path] = None) -> BasketShadow:
    """Load every configured basket and its lab file. Ignores the on/off flags; raises on bad config."""
    root = Path(root)
    baskets, labs = [], {}
    for rel in settings.get("baskets") or ["config/baskets/india.yaml"]:
        b = load_basket(root / rel)
        baskets.append(b)
        labs[b.market] = load_lab(b, root)
    out = Path(out_dir) if out_dir else root / str(settings.get("out_dir") or "data/shadow/basket")
    return BasketShadow(baskets, out_dir=out, founder_off_file=founder_off_path(settings, root), labs=labs)


def basket_parity(**replay_kw: Any) -> dict[str, Any]:
    """Legacy replay vs the event path with the selector forced on (rows to a temp dir). Paper only."""
    import tempfile

    from desk_ml.event_parity import compare_boards, summarize
    from desk_ml.paper_scalp import replay_paper_scalp
    from desk_ml.persist import repo_root

    kw = {**replay_kw, "write": False}
    old = replay_paper_scalp(**kw, use_event_bus=False)
    with tempfile.TemporaryDirectory() as tmp:
        conf = repo_root()  # basket config always comes from this checkout; `root` only feeds the replay
        shadow = build_shadow(load_settings(conf), root=conf, out_dir=Path(tmp))
        shadow.founder_off_file = None  # a parity run must exercise the selector
        new = replay_paper_scalp(**kw, event_session=BasketEventSession(basket=shadow))
    problems = compare_boards(old, new)
    basket = (new.get("event_bus") or {}).get("basket_shadow") or {}
    if basket.get("errors"):
        problems.append(f"basket errors: {basket['errors'][:3]}")
    return {"ok": not problems, "problems": problems, "old": summarize(old.get("closed_trades") or []),
            "new": summarize(new.get("closed_trades") or []), "basket": basket}


# ------------------------------------------------------------------ event-bus wiring (no boss edits)


class BasketBus:
    """Connects a `BasketShadow` to an event session's bus. Subscribes only; never publishes.

    MARKET_TICK (priority 15: after the desk's mark-to-market at 10, before the boss decides at 20):
    the first tick of an index and day triggers `pre_open`, and every tick sets the clock that
    REGIME_LABEL is checked against. REGIME_LABEL is published by the regime service while the boss
    handles that same tick, so each label is judged against the tick it was computed on.
    Any error is logged and kept in `errors`; it never reaches `bus.errors` or the entry path.
    """

    def __init__(self, shadow: BasketShadow, bus: Any, engine: Any, steps: Optional[Mapping[str, Any]] = None,
                 *, label_version: Optional[str] = None) -> None:
        self.shadow, self.bus, self.engine = shadow, bus, engine
        self.steps = steps if steps is not None else {}
        self.label_version = label_version
        self.now_ts: Optional[int] = None
        self.errors: list[str] = []
        self._opened: set[tuple[str, str]] = set()
        self.subs = [
            bus.subscribe(["MARKET_TICK"], self.on_tick, priority=15),
            bus.subscribe(["REGIME_LABEL"], self.on_label, priority=50),
        ]

    def _fail(self, where: str, exc: Exception) -> None:
        if len(self.errors) < 20:
            self.errors.append(f"{where}: {type(exc).__name__}: {exc}")
        log.exception("basket selector %s failed; entries unaffected", where)

    def on_tick(self, event: Any) -> None:
        try:
            p = event.payload
            und, ts = str(p["underlying"]).upper(), int(p["ts"])
            self.now_ts = ts
            day = ist_date(ts)
            if (und, day) in self._opened:
                return
            self._opened.add((und, day))
            step = self.steps.get(p.get("key"))
            self.shadow.pre_open(und, ts, expiry_day=self._expiry_day(step, und, ts, day), version=self.label_version)
        except Exception as exc:
            self._fail("pre_open", exc)

    def on_label(self, event: Any) -> None:
        try:
            if self.now_ts is not None:
                self.shadow.on_label(event.payload, self.now_ts)
        except Exception as exc:
            self._fail("on_label", exc)

    def _expiry_day(self, step: Any, und: str, ts: int, day: str) -> bool:
        """Same expiry calendar the regime labeller is given for this session (desk_ml.regime.shadow)."""
        from desk_ml.regime.labels import next_expiry
        from desk_ml.regime.shadow import _expiry_dates

        exp = next_expiry(date.fromisoformat(day), _expiry_dates(self.engine, getattr(step, "tick", None), und, ts, day))
        return exp is not None and exp.isoformat() == day

    def summary(self) -> dict[str, Any]:
        return {**self.shadow.summary(), "errors": list(self.errors)}


def attach_from_settings(bus: Any, engine: Any, steps: Optional[Mapping[str, Any]] = None, *,
                         root: Optional[Path] = None, shadow: Optional[BasketShadow] = None) -> Optional[BasketBus]:
    """The one-line integration point for `EventSession.attach` (docs/baskets.md). None when off."""
    from desk_ml.persist import repo_root
    from desk_ml.regime import load_config

    root = Path(root or repo_root())
    shadow = shadow if shadow is not None else shadow_from_settings(load_settings(root), root=root)
    if shadow is None:
        return None
    try:
        version = load_config(root).labels.version
    except Exception:
        version = None
    return BasketBus(shadow, bus, engine, steps, label_version=version)


def _event_session_class() -> type:
    from desk_ml.event_path import EventSession

    class _BasketEventSession(EventSession):
        """`EventSession` plus the basket selector, for replays and tests until the one-line hook lands.

        ``basket``: None = read config/baskets/selector.yaml (off by default), False = off, or a BasketShadow.
        """

        def __init__(self, *, basket: Any = None, **kw: Any) -> None:
            super().__init__(**kw)
            self._basket_arg = basket
            self.basket_bus: Optional[BasketBus] = None

        def attach(self, engine: Any) -> "EventSession":
            super().attach(engine)
            if self._basket_arg is not False:
                self.basket_bus = attach_from_settings(self.bus, engine, self.steps, shadow=self._basket_arg)
            return self

        def summary(self) -> dict[str, Any]:
            out = super().summary()
            if self.basket_bus is not None:
                out["basket_shadow"] = self.basket_bus.summary()
            return out

    return _BasketEventSession


def BasketEventSession(**kw: Any) -> Any:  # noqa: N802 - reads like the class it builds
    return _event_session_class()(**kw)


# ----------------------------------------------------------------------- CLI


def main(argv: Optional[Sequence[str]] = None) -> int:
    from desk_ml.persist import repo_root

    ap = argparse.ArgumentParser(prog="python -m strategy_basket",
                                 description="Strategy basket: validate lab output, founder on/off.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a lab basket JSON against its config/baskets/<market>.yaml")
    v.add_argument("path", type=Path)
    for name in ("off", "on", "status"):
        sub.add_parser(name, help=f"founder control: {name}")
    par = sub.add_parser("parity", help="recorded days: legacy replay vs event path with the selector on")
    par.add_argument("--since", default="2026-09-17")
    par.add_argument("--until", default="2026-09-25")
    par.add_argument("--days", nargs="*", help="explicit IST dates (overrides --since/--until)")
    par.add_argument("--underlyings", nargs="*", default=["NIFTY"])
    par.add_argument("--source", default="dual-tape")
    par.add_argument("--no-live-session", action="store_true", help="historical replay instead of live-session params")
    par.add_argument("--kw", action="append", default=[], metavar="KEY=JSON", help="extra replay_paper_scalp kwarg")
    args = ap.parse_args(argv)
    root = repo_root()
    settings = load_settings(root)
    founder = founder_off_path(settings, root)
    if args.cmd == "validate":
        try:
            market = json.loads(args.path.read_text(encoding="utf-8")).get("market")
            cards, rejected, until = load_lab_basket(args.path, load_basket(root / "config" / "baskets" / f"{market}.yaml"))
        except (OSError, ValueError, AttributeError) as exc:
            print(f"REJECTED file: {exc}")
            return 1
        print(json.dumps({"accepted": sorted(cards), "rejected": rejected, "data_until": until}, indent=2))
        return 1 if rejected else 0
    if args.cmd == "parity":
        return _parity_cli(args, root)
    if args.cmd == "off":
        founder.parent.mkdir(parents=True, exist_ok=True)
        founder.write_text("basket selector switched off by founder\n", encoding="utf-8")
    elif args.cmd == "on" and founder.exists():
        founder.unlink()
    print(json.dumps({"enabled_flag": enabled(settings), "founder_off": founder.exists(), "founder_off_file": str(founder)}))
    return 0


def _parity_cli(args: Any, root: Path) -> int:
    from desk_ml.event_parity import _kw
    from desk_ml.paper_scalp import list_fix_first_days

    days = args.days or [d for d in list_fix_first_days(root=root, since=args.since) if d <= args.until]
    if not days:
        print(f"no dual-tape days in {root}/data/recon/paper_watch/DUAL-TAPE for {args.since}..{args.until}")
        return 1
    tot = {"old": [0, 0.0], "new": [0, 0.0]}
    ok = True
    for day in days:
        rep = basket_parity(root=root, underlyings=tuple(args.underlyings), source=args.source,
                            live_session=not args.no_live_session, session_ist_date=day, **_kw(args.kw))
        ok = ok and rep["ok"]
        for side in ("old", "new"):
            tot[side][0] += rep[side]["n_trades"]
            tot[side][1] = round(tot[side][1] + rep[side]["net_pnl_inr"], 2)
        print(f"{day}: {'PARITY' if rep['ok'] else 'MISMATCH'} old {rep['old']} new {rep['new']} "
              f"basket rows {rep['basket'].get('rows')} labels {rep['basket'].get('labels_seen')}")
        for p in rep["problems"][:10]:
            print(f"    {p}")
    print(f"TOTAL old {{'n_trades': {tot['old'][0]}, 'net_pnl_inr': {tot['old'][1]}}} "
          f"new {{'n_trades': {tot['new'][0]}, 'net_pnl_inr': {tot['new'][1]}}} -> {'PARITY' if ok else 'MISMATCH'}")
    return 0 if ok else 1

