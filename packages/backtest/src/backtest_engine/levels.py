"""Named SL/TP level builders. No silent hardcoded strategy.

Methods are MIX / method ids. DESK_PLACEHOLDER is deprecated and labeled.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence  # Any used by quarantine / validators

from backtest_engine.indicators import Bar, _wilder_atr

# Deprecated desk placeholder — never present as an unnamed strategy.
DESK_PLACEHOLDER_STOP_PTS = {"NIFTY": 30.0, "BANKNIFTY": 60.0, "SENSEX": 100.0}
STRIKE_STEP = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}

# Default paper method when ATR seed exists (MIX-DESK-IQ-ATR-RR2 / MIX-SLTP-ATR-R2).
DEFAULT_LEVELS_METHOD = "MIX-SLTP-ATR-R2"
DEFAULT_ATR_PERIOD = 14
DEFAULT_ATR_MULT = 1.5
DEFAULT_RR = 2.0

# MIX-SLTP-PREM-PCT / STRAT-002: premium target mid of 20–30% of entry premium.
# Stop: MIX-SLTP-SWING-STOP — underlying recent fractal swing (HAUSZx SOURCE_FACT
# structure / HYPOTHESIS PAPER bind). Premium-% stop refused unless stop_pct given.
DEFAULT_PREMIUM_TARGET_PCT = 0.25
PREMIUM_LEVELS_METHOD = "MIX-SLTP-PREM-PCT"
SWING_STOP_METHOD = "MIX-SLTP-SWING-STOP"
DEFAULT_SWING_WING = 2


def round_strike(spot: float, underlying: str) -> int:
    step = STRIKE_STEP.get(underlying, 50)
    return int(round(spot / step) * step)


def atr_at(bars: Sequence[Bar], period: int = DEFAULT_ATR_PERIOD) -> Optional[float]:
    if not bars:
        return None
    atrs = _wilder_atr(list(bars), period)
    for v in reversed(atrs):
        if v is not None:
            return float(v)
    return None


def _empty(*, note: str, method_id: str) -> dict[str, Any]:
    return {
        "strike": None,
        "entry": None,
        "stop": None,
        "target": None,
        "unit": "INDEX_POINTS_PROXY",
        "levels_ready": False,
        "levels_method": method_id,
        "levels_note": note,
        "mix_id": method_id,
    }


def build_levels(
    *,
    underlying: str,
    lean: str,
    spot: Optional[float],
    state: str,
    method_id: str = DEFAULT_LEVELS_METHOD,
    atr_value: Optional[float] = None,
    atr_mult: float = DEFAULT_ATR_MULT,
    rr: float = DEFAULT_RR,
    bars: Optional[Sequence[Bar]] = None,
) -> dict[str, Any]:
    """Strategy-selected paper levels. Option premium UNKNOWN until chain binds."""
    if lean not in ("CE", "PE") or spot is None or state in (
        "VETOED",
        "EXPIRED",
        "WATCH",
        "EARLY",
    ):
        return _empty(
            method_id=method_id,
            note=(
                "No live ticket levels while the lean is mixing, early, or held. "
                "EARLY is not a fill."
            ),
        )

    method = (method_id or DEFAULT_LEVELS_METHOD).upper()
    entry = round(float(spot), 2)
    strike = round_strike(float(spot), underlying)

    if method in ("MIX-SLTP-ATR-R2", "MIX-DESK-IQ-ATR-RR2"):
        atr = atr_value
        if atr is None and bars is not None:
            atr = atr_at(bars, DEFAULT_ATR_PERIOD)
        if atr is None or atr <= 0:
            return _empty(
                method_id=method,
                note=(
                    f"{method}: DATA_INSUFFICIENT — ATR({DEFAULT_ATR_PERIOD}) seed missing. "
                    "Refusing fake fixed points. Not a fill."
                ),
            )
        stop_d = float(atr) * float(atr_mult)
        target_d = stop_d * float(rr)
        return _packed(
            lean=lean,
            strike=strike,
            entry=entry,
            stop_d=stop_d,
            target_d=target_d,
            method_id=method,
            unit="INDEX_POINTS_PROXY",
            rr=rr,
            extra={
                "atr": round(float(atr), 4),
                "atr_period": DEFAULT_ATR_PERIOD,
                "atr_mult": atr_mult,
                "levels_note": (
                    f"Paper levels from {method}: ATR({DEFAULT_ATR_PERIOD})×{atr_mult} stop, "
                    f"R×{rr} target (index proxy, not option premium). You decide. Orders refused."
                ),
            },
        )

    if method == "MIX-SLTP-ST-FLIP":
        # Ticket shows prefer RR as honesty label; exit is ST flip (no fixed stop points).
        return {
            "strike": strike,
            "entry": entry,
            "stop": None,
            "target": None,
            "unit": "SUPERTREND_FLIP",
            "levels_ready": True,
            "levels_method": method,
            "mix_id": method,
            "rr_prefer": 2.0,
            "levels_note": (
                "MIX-SLTP-ST-FLIP: exit = 3m close through Supertrend (STRAT-003). "
                "No fixed index-point stop on the ticket. Prefer RR 2.0 is preference only."
            ),
        }

    if method == "MIX-SLTP-PREM-PCT":
        return {
            "strike": strike,
            "entry": None,
            "stop": None,
            "target": None,
            "unit": "OPTION_PREMIUM_PCT",
            "levels_ready": False,
            "levels_method": method,
            "mix_id": method,
            "target_premium_pct_range": [0.20, 0.30],
            "levels_note": (
                "MIX-SLTP-PREM-PCT (STRAT-002): needs option LTP. "
                "DATA_INSUFFICIENT on index-only ticket. Never attach to STRAT-003."
            ),
        }

    if method in ("DESK_PLACEHOLDER", "STOP_PTS_DEPRECATED"):
        stop_d = DESK_PLACEHOLDER_STOP_PTS.get(underlying, 30.0)
        target_d = stop_d * 2.0
        return _packed(
            lean=lean,
            strike=strike,
            entry=entry,
            stop_d=stop_d,
            target_d=target_d,
            method_id="DESK_PLACEHOLDER",
            unit="INDEX_POINTS_PROXY",
            rr=2.0,
            extra={
                "deprecated": True,
                "levels_note": (
                    "DEPRECATED DESK_PLACEHOLDER fixed index points — not a named teacher strategy. "
                    "Prefer MIX-SLTP-ATR-R2 / MIX-DESK-IQ-ATR-RR2 when ATR exists."
                ),
            },
        )

    return _empty(
        method_id=method,
        note=f"Unknown levels method {method}. DATA_INSUFFICIENT — no silent hardcode.",
    )


def _packed(
    *,
    lean: str,
    strike: int,
    entry: float,
    stop_d: float,
    target_d: float,
    method_id: str,
    unit: str,
    rr: float,
    extra: dict[str, Any],
) -> dict[str, Any]:
    if lean == "CE":
        stop = round(entry - stop_d, 2)
        target = round(entry + target_d, 2)
    else:
        stop = round(entry + stop_d, 2)
        target = round(entry - target_d, 2)
    out: dict[str, Any] = {
        "strike": strike,
        "entry": entry,
        "stop": stop,
        "target": target,
        "unit": unit,
        "levels_ready": True,
        "levels_method": method_id,
        "mix_id": method_id,
        "rr_prefer": rr,
        "stop_pts": round(stop_d, 4),
        "target_pts": round(target_d, 4),
    }
    out.update(extra)
    return out


def index_level_floor(underlying: Optional[str] = None) -> float:
    """Below this, a numeric ticket slot is almost never an index print."""
    if underlying == "BANKNIFTY":
        return 5000.0
    if underlying == "SENSEX":
        return 10000.0
    return 1000.0


def looks_like_index_level(value: Any, underlying: Optional[str] = None) -> bool:
    """True when a number is index-magnitude (not a typical option premium)."""
    if value is None or value == "":
        return False
    try:
        n = float(value)
    except (TypeError, ValueError):
        return False
    return n >= index_level_floor(underlying)


def _is_missing_or_di(value: Any) -> bool:
    if value is None or value == "":
        return True
    s = str(value).strip().upper()
    return s in (
        "DATA_INSUFFICIENT",
        "DI",
        "UNKNOWN",
        "—",
        "-",
        "N/A",
        "NA",
    )


def _is_fractal_swing_high(bars: Sequence[Bar], i: int, *, wing: int) -> bool:
    if i < wing or i + wing >= len(bars):
        return False
    hi = bars[i].high
    for j in range(i - wing, i + wing + 1):
        if j == i:
            continue
        if bars[j].high > hi:
            return False
    return True


def _is_fractal_swing_low(bars: Sequence[Bar], i: int, *, wing: int) -> bool:
    if i < wing or i + wing >= len(bars):
        return False
    lo = bars[i].low
    for j in range(i - wing, i + wing + 1):
        if j == i:
            continue
        if bars[j].low < lo:
            return False
    return True


def recent_swing_underlying_stop(
    bars: Sequence[Bar],
    lean: str,
    *,
    wing: int = DEFAULT_SWING_WING,
) -> Optional[float]:
    """Last confirmed fractal swing on the underlying (PAPER / HYPOTHESIS).

    SOURCE_FACT (HAUSZx): ultimate stop = recent swing of underlying, not option
    premium chart. CE → swing low; PE → swing high. Returns None when bars are
    too short or no confirmed swing exists — never invents a premium-% stop.
    Layer: structure = SOURCE_FACT teacher rule; numeric fractal wing = HYPOTHESIS.
    """
    side = str(lean or "").upper().replace("BUY_", "")
    if side not in ("CE", "PE") or not bars:
        return None
    w = max(1, int(wing))
    # Search from most recent confirmed pivot (exclude unfinished right wing).
    last_i = len(bars) - 1 - w
    for i in range(last_i, w - 1, -1):
        if side == "CE" and _is_fractal_swing_low(bars, i, wing=w):
            return round(float(bars[i].low), 2)
        if side == "PE" and _is_fractal_swing_high(bars, i, wing=w):
            return round(float(bars[i].high), 2)
    return None


def bind_option_premium_levels(
    *,
    option_ltp: float,
    lean: str,
    strike: Optional[int] = None,
    underlying_spot: Optional[float] = None,
    target_pct: float = DEFAULT_PREMIUM_TARGET_PCT,
    stop_pct: Optional[float] = None,
    method_id: str = PREMIUM_LEVELS_METHOD,
    expiry: Optional[str] = None,
    premium_source: str = "dhan_optionchain",
    bars: Optional[Sequence[Bar]] = None,
    swing_wing: int = DEFAULT_SWING_WING,
) -> dict[str, Any]:
    """Customer ticket premium slots from live option LTP.

    Documented rule (MIX-SLTP-PREM-PCT / STRAT-002 + MIX-SLTP-SWING-STOP):
      Entry = option LTP
      Target = entry × (1 + target_pct)  # default 0.25 = mid of 20–30%
      Stop (premium slot) = entry × (1 − stop_pct) only when stop_pct is explicit;
           else premium Stop stays DI. When ``bars`` present, bind
           ``index_stop`` / ``stop_underlying`` via MIX-SLTP-SWING-STOP
           (underlying recent fractal swing). Never invent a silent premium-%.

    Long CE and long PE both profit when premium rises — stop below / target above.
    """
    side = str(lean or "").upper().replace("BUY_", "")
    entry = round(float(option_ltp), 2)
    if entry <= 0:
        return {
            "strike": strike,
            "entry": None,
            "stop": None,
            "target": None,
            "unit": "OPTION_PREMIUM",
            "levels_ready": False,
            "levels_method": method_id,
            "mix_id": method_id,
            "underlying_spot": underlying_spot,
            "expiry": expiry,
            "premium_source": premium_source,
            "levels_note": (
                "DATA_INSUFFICIENT: option LTP non-positive — refusing premium bind. "
                "Not a fill. Orders refused."
            ),
        }

    target = round(entry * (1.0 + float(target_pct)), 2)
    stop: Any = None
    stop_note = (
        f"{method_id}: premium Stop = DATA_INSUFFICIENT — teacher stop is "
        f"{SWING_STOP_METHOD} on underlying (not a premium-% invent)."
    )
    if stop_pct is not None and float(stop_pct) > 0:
        stop = round(entry * (1.0 - float(stop_pct)), 2)
        if stop <= 0:
            stop = None
            stop_note = (
                f"{method_id}: stop_pct produced non-positive stop — DATA_INSUFFICIENT."
            )
        else:
            stop_note = (
                f"{method_id}: Stop = entry×(1−{float(stop_pct):.2f}) "
                "(explicit premium stop_pct). Not a fill."
            )

    swing = recent_swing_underlying_stop(bars or [], side, wing=swing_wing)
    # Entry+target bound from LTP counts as premium-ready; premium stop may stay DI.
    levels_ready = True
    note_bits = [
        f"{method_id}: Entry = option LTP ({premium_source}). "
        f"Target = entry×(1+{float(target_pct):.2f}) mid of STRAT-002 20–30%.",
        stop_note,
        "You decide. Orders refused.",
    ]
    out: dict[str, Any] = {
        "strike": strike,
        "entry": entry,
        "stop": stop,
        "target": target,
        "unit": "OPTION_PREMIUM",
        "levels_ready": levels_ready,
        "levels_method": method_id,
        "mix_id": method_id,
        "underlying_spot": underlying_spot,
        "expiry": expiry,
        "premium_source": premium_source,
        "premium_ltp": entry,
        "target_premium_pct": float(target_pct),
        "levels_note": " ".join(note_bits),
    }
    if swing is not None:
        out["index_stop"] = swing
        out["stop_underlying"] = swing
        out["stop_basis"] = "UNDERLYING_RECENT_SWING"
        out["stop_method"] = SWING_STOP_METHOD
        out["stop_layer"] = "HYPOTHESIS"
        out["stop_source_fact"] = "HAUSZx ultimate stop = recent swing of underlying"
        note_bits.insert(
            -1,
            f"{SWING_STOP_METHOD}: underlying swing bound at {swing} "
            "(chart/index_stop). Premium ticket Stop stays DI without greeks map.",
        )
        out["levels_note"] = " ".join(note_bits)
        if stop is None:
            out["stop_gap"] = (
                f"DATA_INSUFFICIENT: premium Stop unbound — {SWING_STOP_METHOD} "
                f"set index_stop={swing}; refusing premium-% invent / greek map"
            )
    elif stop is None:
        out["stop_gap"] = (
            f"DATA_INSUFFICIENT: {SWING_STOP_METHOD} needs underlying bars "
            "(or explicit stop_pct); premium-% invent refused"
        )
    return out


def quarantine_index_proxy_from_customer_ticket(
    levels: dict[str, Any],
    *,
    underlying_spot: Optional[float] = None,
    option_ltp: Optional[float] = None,
    lean: Optional[str] = None,
    premium_meta: Optional[dict[str, Any]] = None,
    bars: Optional[Sequence[Bar]] = None,
) -> dict[str, Any]:
    """Move INDEX_POINTS_PROXY entry/stop/target off customer premium slots.

    Chart / research may keep index_* keys. Customer ticket entry/stop/target
    stay empty until option premium LTP binds — never invent premium from index.
    When option_ltp is provided, bind MIX-SLTP-PREM-PCT premium levels.
    When bars are provided, MIX-SLTP-SWING-STOP fills index_stop / stop_underlying.
    """
    out = dict(levels or {})
    unit = str(out.get("unit") or "").upper()
    meta = premium_meta or {}

    if option_ltp is not None and float(option_ltp) > 0 and lean in ("CE", "PE", "BUY_CE", "BUY_PE"):
        # Preserve index_* from prior proxy if present.
        idx_entry = out.get("index_entry", out.get("entry") if unit.startswith("INDEX") else None)
        idx_stop = out.get("index_stop", out.get("stop") if unit.startswith("INDEX") else None)
        idx_target = out.get("index_target", out.get("target") if unit.startswith("INDEX") else None)
        bound = bind_option_premium_levels(
            option_ltp=float(option_ltp),
            lean=str(lean),
            strike=meta.get("strike") or out.get("strike"),
            underlying_spot=(
                underlying_spot
                if underlying_spot is not None
                else meta.get("underlying_spot")
            ),
            expiry=meta.get("expiry"),
            premium_source=str(meta.get("source") or "dhan_optionchain"),
            bars=bars,
        )
        if idx_entry is not None and bound.get("index_entry") is None:
            bound["index_entry"] = idx_entry
        # Prefer swing-bound index_stop when present; else keep ATR proxy stop.
        if bound.get("index_stop") is None and idx_stop is not None:
            bound["index_stop"] = idx_stop
        if idx_target is not None and bound.get("index_target") is None:
            bound["index_target"] = idx_target
        return bound

    if unit not in ("INDEX_POINTS_PROXY", "INDEX_POINTS", "SUPERTREND_FLIP"):
        # Already premium-shaped or DI — leave alone, but stamp gap reason if provided.
        if underlying_spot is not None and out.get("underlying_spot") is None:
            out["underlying_spot"] = underlying_spot
        if meta.get("reason") and not out.get("levels_ready"):
            gap = str(meta["reason"])
            out["levels_gap"] = gap
            out["levels_note"] = (
                f"{gap}. Index path stays on chart/index_* — not Entry/SL/Target. "
                "Not a fill. Orders refused."
            )
            if meta.get("source"):
                out["premium_source"] = meta["source"]
        return out

    idx_entry = out.get("entry")
    idx_stop = out.get("stop")
    idx_target = out.get("target")
    spot = underlying_spot if underlying_spot is not None else idx_entry
    gap = (
        str(meta.get("reason"))
        if meta.get("reason")
        else "DATA_INSUFFICIENT: option premium LTP unbound / OPTIDX premium not fetched"
    )
    out["index_entry"] = idx_entry
    out["index_stop"] = idx_stop
    out["index_target"] = idx_target
    out["underlying_spot"] = spot
    out["entry"] = None
    out["stop"] = None
    out["target"] = None
    out["unit"] = "OPTION_PREMIUM"
    out["levels_ready"] = False
    out["levels_gap"] = gap
    out["levels_note"] = (
        f"{gap}. "
        "Index path levels quarantined to chart/index_* — not Entry/SL/Target. "
        "Not a fill. Orders refused."
    )
    return out


def validate_index_proxy_levels(
    *,
    lean: str,
    entry: Optional[float],
    stop: Optional[float],
    target: Optional[float],
    underlying: Optional[str] = None,
) -> list[str]:
    """Detect inverted or premium-shaped levels on INDEX_POINTS_PROXY tickets.

    BUY_CE index proxy: stop < entry < target.
    BUY_PE index proxy: stop > entry > target.
    Does not invent fills. Empty/missing levels are not bugs.
    """
    bugs: list[str] = []
    if entry is None or stop is None or target is None:
        return bugs
    try:
        e, s, t = float(entry), float(stop), float(target)
    except (TypeError, ValueError):
        return ["LEVELS_NON_NUMERIC"]

    side = str(lean or "").upper().replace("BUY_", "")
    # Index underlyings trade in the thousands; sub-1k entry is almost always
    # a mistaken option-premium placeholder on an INDEX_POINTS_PROXY ticket.
    floor = index_level_floor(underlying)
    if 0 < e < floor:
        bugs.append(
            "SUSPECT_PREMIUM_AS_INDEX: entry looks like option premium on "
            "INDEX_POINTS_PROXY ticket (not a fill; refuse as customer ticket)"
        )

    if side == "PE":
        if not (s > e > t):
            bugs.append(
                "PE_INDEX_LEVELS_INVERTED: expect stop > entry > target for BUY_PE index proxy"
            )
    elif side == "CE":
        if not (s < e < t):
            bugs.append(
                "CE_INDEX_LEVELS_INVERTED: expect stop < entry < target for BUY_CE index proxy"
            )
    return bugs


def validate_customer_option_premium_slots(
    *,
    side: str,
    entry: Any,
    stop: Any,
    target: Any,
    underlying: Optional[str] = None,
    unit: Optional[str] = None,
) -> list[str]:
    """Customer BUY_CE/BUY_PE ticket slots must be premium or DI — never index.

    Founder rule: do not put NIFTY/SENSEX index prints into Entry/SL/Target.
    """
    lean = str(side or "").upper()
    if lean not in ("BUY_CE", "BUY_PE", "CE", "PE"):
        return []

    bugs: list[str] = []
    u = str(unit or "").upper()
    if u in ("INDEX_POINTS_PROXY", "INDEX_POINTS"):
        if not all(_is_missing_or_di(v) for v in (entry, stop, target)):
            bugs.append(
                "INDEX_AS_PREMIUM: INDEX_POINTS_PROXY must not occupy customer "
                "Entry/SL/Target for CE/PE buys (quarantine to chart/index_*)"
            )
        return bugs

    for key, val in (("entry", entry), ("stop", stop), ("target", target)):
        if _is_missing_or_di(val):
            continue
        if looks_like_index_level(val, underlying):
            bugs.append(
                f"INDEX_AS_PREMIUM: customer {key} looks like index level "
                f"({val}) — refuse; show DATA_INSUFFICIENT until premium LTP binds"
            )
    return bugs
