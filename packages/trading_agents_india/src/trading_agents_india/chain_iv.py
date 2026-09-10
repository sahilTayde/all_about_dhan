"""Chain IV-surface stats gather: parse, compute, persist, load.

This is the `chain_iv_stats` gather ticket from the algos.dhan.co study
(teams/01_research/docs/DHAN_ALGO_MARKETPLACE_STRATZY.md §4). Dhan's
documented POST /optionchain returns implied_volatility per strike on both
sides; desk_intel.parse_oc drops it, so this module parses IV straight from
the raw ``data.oc`` payload. Per snapshot we persist three surface-shape
statistics for MIX-ALGO-SKEW-BUY / MIX-ALGO-IV-REGIME-HOLD research:

- skew_tilt   = mean(OTM PE IV) - mean(OTM CE IV) over ATM±k wings.
                Positive = put smirk (downside protection rich).
- curvature   = wing-mean IV minus 2x ATM IV (positive = smile bows up).
- iv_entropy  = normalized Shannon entropy of mid-IV weights across ATM±k
                (1.0 = perfectly flat surface, lower = concentrated shape).

Dhan has no historical IV endpoint, so this history exists only from the day
the gather starts. Fail soft: errors are DATA_INSUFFICIENT gaps, never
invented numbers. HYPOTHESIS layer inputs only — no orders, no promotes.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from trading_agents_india.session_clock import now_ist

# VERIFY vs workspace.yaml / instrument master — same hints as hooks/chain.py.
_SCRIP_HINTS = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "SENSEX": (51, "IDX_I"),
}

DEFAULT_WING = 5  # strikes each side of ATM used for tilt/curvature/entropy


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def chain_iv_dir() -> Path:
    path = _repo_root() / "data" / "recon" / "chain_iv"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class IvPoint:
    strike: float
    ce_iv: Optional[float] = None
    pe_iv: Optional[float] = None

    @property
    def mid_iv(self) -> Optional[float]:
        vals = [v for v in (self.ce_iv, self.pe_iv) if v is not None and v > 0]
        if not vals:
            return None
        return sum(vals) / len(vals)


@dataclass
class ChainIvResult:
    underlying: str
    source: str  # dhan_optionchain | payload | unavailable
    day: str = ""
    stats: Optional[dict[str, Any]] = None
    path: str = ""
    data_gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unwrap(payload: Any) -> Optional[dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict) and "oc" in data:
        return data
    if "oc" in payload:
        return payload
    if isinstance(data, dict) and isinstance(data.get("data"), dict) and "oc" in data["data"]:
        return data["data"]
    return None


def _opt_pos_float(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


def parse_iv_points(payload: Any) -> tuple[Optional[float], list[IvPoint]]:
    """Extract (spot, per-strike IV points) from a documented chain payload."""
    data = _unwrap(payload)
    if data is None:
        return None, []
    try:
        spot = float(data.get("last_price"))
    except (TypeError, ValueError):
        spot = None
    oc = data.get("oc")
    points: list[IvPoint] = []
    items: list[tuple[Any, Any]]
    if isinstance(oc, dict):
        items = list(oc.items())
    elif isinstance(oc, list):
        items = [(cell.get("strike"), cell) for cell in oc if isinstance(cell, dict)]
    else:
        return spot, []
    for strike_key, cell in items:
        if not isinstance(cell, dict):
            continue
        try:
            strike = float(strike_key if strike_key not in (None, "") else cell.get("strike"))
        except (TypeError, ValueError):
            continue
        ce = cell.get("ce") if isinstance(cell.get("ce"), dict) else {}
        pe = cell.get("pe") if isinstance(cell.get("pe"), dict) else {}
        points.append(
            IvPoint(
                strike=strike,
                ce_iv=_opt_pos_float(ce.get("implied_volatility")),
                pe_iv=_opt_pos_float(pe.get("implied_volatility")),
            )
        )
    points.sort(key=lambda p: p.strike)
    return spot, points


def compute_iv_stats(
    spot: Optional[float],
    points: list[IvPoint],
    *,
    wing: int = DEFAULT_WING,
) -> Optional[dict[str, Any]]:
    """Surface-shape stats around ATM±wing. None when inputs are insufficient."""
    usable = [p for p in points if p.mid_iv is not None]
    if spot is None or len(usable) < 3:
        return None
    atm_i = min(range(len(usable)), key=lambda i: abs(usable[i].strike - spot))
    lo = max(0, atm_i - wing)
    hi = min(len(usable), atm_i + wing + 1)
    window = usable[lo:hi]
    atm = usable[atm_i]

    put_wing = [p.pe_iv for p in window if p.strike < atm.strike and p.pe_iv is not None]
    call_wing = [p.ce_iv for p in window if p.strike > atm.strike and p.ce_iv is not None]
    skew_tilt = None
    if put_wing and call_wing:
        skew_tilt = sum(put_wing) / len(put_wing) - sum(call_wing) / len(call_wing)

    atm_mid = atm.mid_iv
    low_mids = [p.mid_iv for p in window if p.strike < atm.strike and p.mid_iv is not None]
    high_mids = [p.mid_iv for p in window if p.strike > atm.strike and p.mid_iv is not None]
    curvature = None
    if atm_mid is not None and low_mids and high_mids:
        curvature = (
            sum(low_mids) / len(low_mids) + sum(high_mids) / len(high_mids) - 2.0 * atm_mid
        )

    mids = [p.mid_iv for p in window if p.mid_iv is not None]
    iv_entropy = None
    if len(mids) >= 3 and sum(mids) > 0:
        total = sum(mids)
        weights = [m / total for m in mids]
        raw = -sum(w * math.log(w) for w in weights if w > 0)
        iv_entropy = raw / math.log(len(weights))

    return {
        "ts": int(now_ist().timestamp()),
        "as_of_ist": now_ist().isoformat(timespec="seconds"),
        "spot": spot,
        "atm_strike": atm.strike,
        "atm_iv_ce": atm.ce_iv,
        "atm_iv_pe": atm.pe_iv,
        "skew_tilt": round(skew_tilt, 4) if skew_tilt is not None else None,
        "curvature": round(curvature, 4) if curvature is not None else None,
        "iv_entropy": round(iv_entropy, 6) if iv_entropy is not None else None,
        "wing": wing,
        "window_strikes": len(window),
        "strike_count": len(points),
        "iv_present": len(usable),
    }


def _stats_path(underlying: str, day: str) -> Path:
    return chain_iv_dir() / f"{underlying.upper()}_iv_stats_{day}.json"


def persist_iv_stats(underlying: str, stats: dict[str, Any], *, source: str) -> str:
    """Upsert one snapshot into the per-day JSON (dedupe by ts). Returns path."""
    und = underlying.upper()
    day = now_ist().date().isoformat()
    path = _stats_path(und, day)
    rows: dict[int, dict[str, Any]] = {}
    if path.is_file():
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
            for row in blob.get("snapshots") or []:
                if isinstance(row, dict) and isinstance(row.get("ts"), int):
                    rows[row["ts"]] = row
        except (json.JSONDecodeError, TypeError, ValueError):
            rows = {}
    rows[int(stats["ts"])] = stats
    payload = {
        "meta": {
            "underlying": und,
            "day": day,
            "source": source,
            "updated_at_ist": now_ist().isoformat(timespec="seconds"),
            "layer": "SOURCE_FACT",
            "note": (
                "IV-surface shape stats per chain snapshot. Live-only history — "
                "Dhan has no IV backfill. Research input for MIX-ALGO-*, not alpha."
            ),
        },
        "snapshots": [rows[k] for k in sorted(rows)],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def load_iv_stats(underlying: str, *, day: Optional[str] = None) -> list[dict[str, Any]]:
    day = day or now_ist().date().isoformat()
    path = _stats_path(underlying.upper(), day)
    if not path.is_file():
        return []
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
        return [r for r in (blob.get("snapshots") or []) if isinstance(r, dict)]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def tilt_momentum(snapshots: list[dict[str, Any]], *, lookback: int = 3) -> Optional[float]:
    """Change in skew_tilt over the last `lookback` snapshots. None if too few."""
    tilts = [s.get("skew_tilt") for s in snapshots if s.get("skew_tilt") is not None]
    if len(tilts) < lookback + 1:
        return None
    return round(float(tilts[-1]) - float(tilts[-1 - lookback]), 4)


def gather_chain_iv(
    underlying: str,
    *,
    prefer_live: bool = False,
    payload: Optional[dict[str, Any]] = None,
    expiry: Optional[str] = None,
) -> ChainIvResult:
    """Compute + persist IV stats from a given payload or a live chain fetch."""
    und = underlying.upper()
    today = now_ist().date().isoformat()

    if payload is not None:
        spot, points = parse_iv_points(payload)
        stats = compute_iv_stats(spot, points)
        if stats is None:
            return ChainIvResult(
                underlying=und,
                source="payload",
                data_gaps=["DATA_INSUFFICIENT: payload lacks spot or per-strike IV"],
            )
        path = persist_iv_stats(und, stats, source="payload")
        return ChainIvResult(underlying=und, source="payload", day=today, stats=stats, path=path)

    if not prefer_live:
        return ChainIvResult(
            underlying=und,
            source="unavailable",
            data_gaps=["DATA_INSUFFICIENT: chain IV gather not live (prefer_live off)"],
        )

    hint = _SCRIP_HINTS.get(und)
    if hint is None:
        return ChainIvResult(
            underlying=und,
            source="unavailable",
            data_gaps=[f"UNKNOWN: no chain hint for {und}"],
        )
    scrip, seg = hint
    try:
        from dhan_client import DhanClient  # type: ignore
    except Exception:
        return ChainIvResult(
            underlying=und,
            source="unavailable",
            data_gaps=["DATA_INSUFFICIENT: dhan_client not importable"],
        )
    try:
        client = DhanClient(dry_run=False)
        if getattr(client.settings, "dry_run", True):
            client.close()
            return ChainIvResult(
                underlying=und,
                source="unavailable",
                data_gaps=["DATA_INSUFFICIENT: Dhan dry_run — chain IV not live"],
            )
        body_u = {"UnderlyingScrip": scrip, "UnderlyingSeg": seg}
        if not expiry:
            expiries = client.option_chain.expiry_list(body_u)
            data = expiries.get("data") if isinstance(expiries, dict) else None
            if isinstance(data, list) and data:
                expiry = str(data[0])
            elif isinstance(data, dict):
                lst = data.get("expiryList") or data.get("expiries") or []
                expiry = str(lst[0]) if lst else None
        if not expiry:
            client.close()
            return ChainIvResult(
                underlying=und,
                source="unavailable",
                data_gaps=["DATA_INSUFFICIENT: no expiry from Dhan optionchain"],
            )
        raw = client.option_chain.chain({**body_u, "Expiry": expiry})
        client.close()
        spot, points = parse_iv_points(raw)
        stats = compute_iv_stats(spot, points)
        if stats is None:
            return ChainIvResult(
                underlying=und,
                source="unavailable",
                data_gaps=["DATA_INSUFFICIENT: live chain parsed but no usable IV"],
            )
        stats["expiry"] = expiry
        path = persist_iv_stats(und, stats, source="dhan_optionchain")
        return ChainIvResult(
            underlying=und,
            source="dhan_optionchain",
            day=today,
            stats=stats,
            path=path,
        )
    except Exception as exc:  # noqa: BLE001
        return ChainIvResult(
            underlying=und,
            source="unavailable",
            data_gaps=[f"DATA_INSUFFICIENT: chain IV {type(exc).__name__}"],
        )
