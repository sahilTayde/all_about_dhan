"""DhanHQ option-chain snapshots + ATM±N strike-buildup.

Default: morning + every **3 minutes** via POST /optionchain
(https://dhanhq.co/docs/v2/option-chain/ — 1 unique request / 3 seconds).
Three minutes between **full** chain calls is inside that budget.

Each poll **remembers the last snapshot** (`last.json` + timestamped file)
so OI / PCR / ATM CE–PE Δ vs last can feed trend/buildup.

1-minute path: do **not** poll the full chain. Use last snapshot's ATM±N
``security_id``s with POST /marketfeed/quote (1 req/s). OI on quote is
VERIFY FROM DOCS — if missing, tag DATA_INSUFFICIENT.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.rate_limit import MinIntervalGate

from config.load import DeskIntelSettings, Market, WorkspaceConfig
from desk_intel.fixtures import fixture_chain
from desk_intel.schema import ChainBias, ChainSnapshot, PollMode, StrikeRow
from desk_intel.store import latest_snapshot, save_snapshot
from desk_intel.time_ist import now_ist_iso

log = logging.getLogger("desk_intel.chain")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _opt_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def unwrap_chain_payload(payload: Any) -> Optional[dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    if payload.get("status") == "dry_run":
        return None
    data = payload.get("data")
    if isinstance(data, dict) and "oc" in data:
        return data
    if isinstance(payload, dict) and "oc" in payload:
        return payload
    if isinstance(data, dict) and isinstance(data.get("data"), dict) and "oc" in data["data"]:
        return data["data"]
    return None


def unwrap_expiry_list(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or payload.get("status") == "dry_run":
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [str(x) for x in data if x]
    return []


def parse_oc(oc: Any) -> list[StrikeRow]:
    """``data.oc`` is keyed by strike string in the official example; also accept a list."""
    rows: list[StrikeRow] = []
    if isinstance(oc, dict):
        items = oc.items()
    elif isinstance(oc, list):
        items = []
        for entry in oc:
            if isinstance(entry, dict):
                strike = entry.get("strike") or entry.get("Strike") or entry.get("strikePrice")
                items.append((strike, entry))
    else:
        return rows

    for strike_key, cell in items:
        if not isinstance(cell, dict):
            continue
        ce = cell.get("ce") or cell.get("CE") or {}
        pe = cell.get("pe") or cell.get("PE") or {}
        if not isinstance(ce, dict):
            ce = {}
        if not isinstance(pe, dict):
            pe = {}
        g_ce = ce.get("greeks") if isinstance(ce.get("greeks"), dict) else {}
        g_pe = pe.get("greeks") if isinstance(pe.get("greeks"), dict) else {}
        rows.append(
            StrikeRow(
                strike=_num(strike_key if strike_key not in (None, "") else cell.get("strike")),
                ce_oi=_int(ce.get("oi")),
                pe_oi=_int(pe.get("oi")),
                ce_oi_prev=_int(ce.get("previous_oi")),
                pe_oi_prev=_int(pe.get("previous_oi")),
                ce_volume=_int(ce.get("volume")),
                pe_volume=_int(pe.get("volume")),
                ce_ltp=_opt_float(ce.get("last_price")),
                pe_ltp=_opt_float(pe.get("last_price")),
                ce_security_id=_int(ce.get("security_id")) or None,
                pe_security_id=_int(pe.get("security_id")) or None,
                ce_gamma=_opt_float(g_ce.get("gamma")),
                pe_gamma=_opt_float(g_pe.get("gamma")),
                ce_delta=_opt_float(g_ce.get("delta")),
                pe_delta=_opt_float(g_pe.get("delta")),
            )
        )
    rows.sort(key=lambda r: r.strike)
    return rows


def nearest_expiry(dates: list[str]) -> Optional[str]:
    if not dates:
        return None
    return sorted(dates)[0]


def atm_index(strikes: list[StrikeRow], spot: Optional[float]) -> Optional[int]:
    if not strikes or spot is None:
        return None
    best_i = 0
    best_d = abs(strikes[0].strike - spot)
    for i, row in enumerate(strikes):
        d = abs(row.strike - spot)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


def max_pain_stub(strikes: list[StrikeRow]) -> Optional[float]:
    """Simple pin: strike minimizing sum of intrinsic * OI. Stub, not a valuation."""
    if not strikes:
        return None
    best_k: Optional[float] = None
    best_pain: Optional[float] = None
    for settle in (row.strike for row in strikes):
        pain = 0.0
        for row in strikes:
            if settle > row.strike:
                pain += (settle - row.strike) * row.ce_oi
            if settle < row.strike:
                pain += (row.strike - settle) * row.pe_oi
        if best_pain is None or pain < best_pain:
            best_pain = pain
            best_k = settle
    return best_k


def wing_slice(strikes: list[StrikeRow], spot: Optional[float], wing: int) -> list[StrikeRow]:
    idx = atm_index(strikes, spot)
    if idx is None:
        return []
    lo = max(0, idx - wing)
    hi = min(len(strikes), idx + wing + 1)
    return strikes[lo:hi]


def compute_chain_bias(
    snap: ChainSnapshot,
    settings: DeskIntelSettings,
    *,
    versus: Optional[ChainSnapshot] = None,
) -> ChainBias:
    """OI/PCR/buildup lean. Operator confirmation happens in fusion, not here."""
    strikes = snap.strikes
    spot = snap.spot
    idx = atm_index(strikes, spot)
    atm = strikes[idx] if idx is not None else None
    ce_oi = sum(r.ce_oi for r in strikes)
    pe_oi = sum(r.pe_oi for r in strikes)
    ce_vol = sum(r.ce_volume for r in strikes)
    pe_vol = sum(r.pe_volume for r in strikes)
    pcr_oi = (pe_oi / ce_oi) if ce_oi else None
    pcr_vol = (pe_vol / ce_vol) if ce_vol else None
    ce_wall = max(strikes, key=lambda r: r.ce_oi).strike if strikes else None
    pe_wall = max(strikes, key=lambda r: r.pe_oi).strike if strikes else None

    if versus and versus.strikes:
        prev_map = {r.strike: r for r in versus.strikes}

        def ce_d(row: StrikeRow) -> int:
            old = prev_map.get(row.strike)
            return row.ce_oi - (old.ce_oi if old else row.ce_oi_prev)

        def pe_d(row: StrikeRow) -> int:
            old = prev_map.get(row.strike)
            return row.pe_oi - (old.pe_oi if old else row.pe_oi_prev)
    else:

        def ce_d(row: StrikeRow) -> int:
            return row.ce_oi_change

        def pe_d(row: StrikeRow) -> int:
            return row.pe_oi_change

    wings = wing_slice(strikes, spot, settings.atm_wing)
    wing_ce = sum(ce_d(r) for r in wings)
    wing_pe = sum(pe_d(r) for r in wings)
    atm_ce_b = ce_d(atm) if atm else 0
    atm_pe_b = pe_d(atm) if atm else 0

    has_prior = bool(versus and versus.strikes)
    vs_last_as_of_ist = versus.as_of_ist if has_prior and versus else None
    pcr_oi_delta: Optional[float] = None
    pcr_volume_delta: Optional[float] = None
    total_ce_oi_delta: Optional[int] = None
    total_pe_oi_delta: Optional[int] = None
    if has_prior and versus is not None:
        prev_ce = sum(r.ce_oi for r in versus.strikes)
        prev_pe = sum(r.pe_oi for r in versus.strikes)
        prev_ce_vol = sum(r.ce_volume for r in versus.strikes)
        prev_pe_vol = sum(r.pe_volume for r in versus.strikes)
        prev_pcr = (prev_pe / prev_ce) if prev_ce else None
        prev_pcr_vol = (prev_pe_vol / prev_ce_vol) if prev_ce_vol else None
        total_ce_oi_delta = ce_oi - prev_ce
        total_pe_oi_delta = pe_oi - prev_pe
        if pcr_oi is not None and prev_pcr is not None:
            pcr_oi_delta = pcr_oi - prev_pcr
        if pcr_vol is not None and prev_pcr_vol is not None:
            pcr_volume_delta = pcr_vol - prev_pcr_vol

    gamma_load = 0.0
    gamma_n = 0
    for row in wings:
        if row.ce_gamma is not None:
            gamma_load += abs(row.ce_gamma) * row.ce_oi
            gamma_n += 1
        if row.pe_gamma is not None:
            gamma_load += abs(row.pe_gamma) * row.pe_oi
            gamma_n += 1

    reasons: list[str] = []
    lean: str = "NEUTRAL"
    # Day/session buildup, not static PCR-as-oracle.
    if wing_ce > wing_pe * 1.25 and wing_ce > 0:
        lean = "CE"
        reasons.append("ATM±N CE OI buildup > PE (call adding — confirm with price, not auto BUY CE)")
    elif wing_pe > wing_ce * 1.25 and wing_pe > 0:
        lean = "PE"
        reasons.append("ATM±N PE OI buildup > CE (put adding — confirm with price, not auto BUY PE)")
    else:
        reasons.append("ATM±N CE/PE buildup not decisive")

    if pcr_oi is not None:
        reasons.append(f"PCR(OI)={pcr_oi:.2f} stub — extreme PCR without price is not a signal")
    if ce_wall is not None:
        reasons.append(f"CE OI wall ~{ce_wall:g} (resistance hypothesis)")
    if pe_wall is not None:
        reasons.append(f"PE OI wall ~{pe_wall:g} (support hypothesis)")
    reasons.append("max-pain is a stub pin estimate, not a magnet proof")
    if has_prior:
        pcr_bit = (
            f"PCR(OI) Δ={pcr_oi_delta:+.3f}"
            if pcr_oi_delta is not None
            else "PCR(OI) Δ n/a"
        )
        reasons.append(
            f"vs last snapshot {vs_last_as_of_ist}: {pcr_bit}; "
            f"ΣCE OI Δ={total_ce_oi_delta:+d} ΣPE OI Δ={total_pe_oi_delta:+d}; "
            f"ATM CE Δ={atm_ce_b:+d} ATM PE Δ={atm_pe_b:+d}"
        )
    else:
        reasons.append(
            "no prior snapshot on disk — ATM CE/PE Δ uses Dhan previous_oi (day), "
            "not 3m memory"
        )

    return ChainBias(
        underlying=snap.underlying,
        expiry=snap.expiry,
        spot=spot,
        atm_strike=atm.strike if atm else None,
        pcr_oi=pcr_oi,
        pcr_volume=pcr_vol,
        max_pain_stub=max_pain_stub(strikes),
        ce_oi_wall=ce_wall,
        pe_oi_wall=pe_wall,
        atm_ce_oi=atm.ce_oi if atm else 0,
        atm_pe_oi=atm.pe_oi if atm else 0,
        atm_ce_buildup=atm_ce_b,
        atm_pe_buildup=atm_pe_b,
        wing_ce_buildup=wing_ce,
        wing_pe_buildup=wing_pe,
        gamma_load_stub=gamma_load if gamma_n else None,
        lean=lean,  # type: ignore[arg-type]
        reasons=reasons,
        as_of_ist=snap.as_of_ist,
        dry_run=snap.dry_run,
        mode=snap.mode,
        vs_last_as_of_ist=vs_last_as_of_ist,
        has_prior_snapshot=has_prior,
        pcr_oi_delta=pcr_oi_delta,
        pcr_volume_delta=pcr_volume_delta,
        total_ce_oi_delta=total_ce_oi_delta,
        total_pe_oi_delta=total_pe_oi_delta,
    )


def _spot_for_fixture(market: Market) -> float:
    # ROOM TO EDIT: fixture spots only. Live path uses data.last_price.
    defaults = {"NIFTY": 25000.0, "BANKNIFTY": 51000.0, "SENSEX": 81000.0}
    return defaults.get(market.id, 25000.0)


def fetch_full_chain(
    client: DhanClient,
    market: Market,
    settings: DeskIntelSettings,
    *,
    mode: PollMode = "full_chain_3m",
    persist: bool = True,
    repo_root: Optional[Any] = None,
) -> ChainSnapshot:
    if market.dhan_underlying_scrip is None:
        log.warning("%s missing dhan_underlying_scrip — using fixture", market.id)
        snap = fixture_chain(market.id, spot=_spot_for_fixture(market), mode=mode, dry_run=True)
        snap.note = "No UnderlyingScrip in workspace.yaml. VERIFY FROM instrument master."
        return snap

    body_u = {
        "UnderlyingScrip": int(market.dhan_underlying_scrip),
        "UnderlyingSeg": market.dhan_underlying_seg or "IDX_I",
    }
    expiries = unwrap_expiry_list(client.option_chain.expiry_list(body_u))
    expiry = nearest_expiry(expiries)
    if client.dry_run or expiry is None:
        if client.dry_run:
            log.info("option chain dry-run for %s — fixture snapshot", market.id)
        else:
            log.warning("no expiry list for %s — fixture", market.id)
        snap = fixture_chain(
            market.id,
            expiry=expiry or "DRY-RUN",
            spot=_spot_for_fixture(market),
            mode=mode,
            dry_run=True,
        )
        if persist and repo_root is not None:
            save_snapshot(
                repo_root,
                settings.snapshots_dir,
                snap,
                remember_last=settings.remember_last_snapshot,
            )
        return snap

    raw = client.option_chain.chain({**body_u, "Expiry": expiry})
    data = unwrap_chain_payload(raw)
    if data is None:
        snap = fixture_chain(market.id, expiry=expiry, mode=mode, dry_run=True)
        snap.note = "Unparsed option-chain payload; fixture used."
        return snap

    snap = ChainSnapshot(
        underlying=market.id,
        expiry=expiry,
        spot=_opt_float(data.get("last_price")),
        as_of_ist=now_ist_iso(),
        mode=mode,
        dry_run=False,
        strikes=parse_oc(data.get("oc")),
        source="dhan_option_chain",
        note="POST /optionchain. Rate limit 1 unique / 3s. Default cadence 3m.",
    )
    if persist and repo_root is not None:
        save_snapshot(
            repo_root,
            settings.snapshots_dir,
            snap,
            remember_last=settings.remember_last_snapshot,
        )
    return snap


def _quote_oi(cell: Any) -> Optional[int]:
    if not isinstance(cell, dict):
        return None
    for key in ("oi", "OI", "open_interest", "openInterest"):
        if cell.get(key) not in (None, ""):
            return _int(cell.get(key))
    return None


def _walk_quote_map(payload: Any) -> dict[int, dict[str, Any]]:
    """Best-effort flatten of market-quote response. Field layout VERIFY FROM DOCS."""
    out: dict[int, dict[str, Any]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            sid = node.get("security_id") or node.get("securityId")
            if sid not in (None, "") and ("oi" in node or "ltp" in node or "last_price" in node):
                try:
                    out[int(sid)] = node
                except (TypeError, ValueError):
                    pass
            for key, value in node.items():
                if str(key).isdigit() and isinstance(value, dict):
                    try:
                        out[int(key)] = value
                    except (TypeError, ValueError):
                        pass
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return out


def fetch_strike_buildup_1m(
    client: DhanClient,
    market: Market,
    settings: DeskIntelSettings,
    *,
    quote_gate: Optional[MinIntervalGate] = None,
    persist: bool = True,
    repo_root: Optional[Any] = None,
) -> ChainSnapshot:
    """ATM±N OI delta via quote API using cached security IDs from last full chain.

    Does not call POST /optionchain every minute.
    """
    previous = None
    if repo_root is not None:
        previous = latest_snapshot(repo_root, settings.snapshots_dir, market.id)
    if previous is None or not previous.strikes:
        log.info("1m buildup needs a cached chain — taking one full snapshot first")
        return fetch_full_chain(
            client,
            market,
            settings,
            mode="morning",
            persist=persist,
            repo_root=repo_root,
        )

    wings = wing_slice(previous.strikes, previous.spot, settings.atm_wing)
    ids = []
    for row in wings:
        if row.ce_security_id:
            ids.append(int(row.ce_security_id))
        if row.pe_security_id:
            ids.append(int(row.pe_security_id))
    ids = sorted(set(ids))
    if not ids:
        log.warning("no security_ids on cached chain for %s", market.id)
        return previous

    if client.dry_run:
        log.info("1m strike-buildup dry-run %s — mutating fixture OI on cached ids", market.id)
        bumped = []
        for row in previous.strikes:
            bumped.append(
                StrikeRow(
                    strike=row.strike,
                    ce_oi=row.ce_oi + 1500,
                    pe_oi=row.pe_oi + 800,
                    ce_oi_prev=row.ce_oi,
                    pe_oi_prev=row.pe_oi,
                    ce_volume=row.ce_volume,
                    pe_volume=row.pe_volume,
                    ce_ltp=row.ce_ltp,
                    pe_ltp=row.pe_ltp,
                    ce_security_id=row.ce_security_id,
                    pe_security_id=row.pe_security_id,
                    ce_gamma=row.ce_gamma,
                    pe_gamma=row.pe_gamma,
                    ce_delta=row.ce_delta,
                    pe_delta=row.pe_delta,
                )
            )
        snap = ChainSnapshot(
            underlying=market.id,
            expiry=previous.expiry,
            spot=previous.spot,
            as_of_ist=now_ist_iso(),
            mode="strike_buildup_1m",
            dry_run=True,
            strikes=bumped,
            source="fixture_quote_delta",
            note="Dry-run 1m path. Live uses POST /marketfeed/quote on ATM±N ids.",
        )
        if persist and repo_root is not None:
            save_snapshot(
                repo_root,
                settings.snapshots_dir,
                snap,
                remember_last=settings.remember_last_snapshot,
            )
        return snap

    body = {market.option_quote_seg or "NSE_FNO": ids}
    if quote_gate is not None:
        quote_gate.wait()
    raw = client.quote.quote(body)
    by_id = _walk_quote_map(raw)
    oi_found = 0
    new_rows: list[StrikeRow] = []
    for row in previous.strikes:
        ce_cell = by_id.get(int(row.ce_security_id)) if row.ce_security_id else None
        pe_cell = by_id.get(int(row.pe_security_id)) if row.pe_security_id else None
        ce_oi = _quote_oi(ce_cell)
        pe_oi = _quote_oi(pe_cell)
        if ce_oi is not None:
            oi_found += 1
        if pe_oi is not None:
            oi_found += 1
        new_rows.append(
            StrikeRow(
                strike=row.strike,
                ce_oi=ce_oi if ce_oi is not None else row.ce_oi,
                pe_oi=pe_oi if pe_oi is not None else row.pe_oi,
                ce_oi_prev=row.ce_oi,
                pe_oi_prev=row.pe_oi,
                ce_volume=row.ce_volume,
                pe_volume=row.pe_volume,
                ce_ltp=_opt_float((ce_cell or {}).get("ltp") or (ce_cell or {}).get("last_price")) or row.ce_ltp,
                pe_ltp=_opt_float((pe_cell or {}).get("ltp") or (pe_cell or {}).get("last_price")) or row.pe_ltp,
                ce_security_id=row.ce_security_id,
                pe_security_id=row.pe_security_id,
                ce_gamma=row.ce_gamma,
                pe_gamma=row.pe_gamma,
                ce_delta=row.ce_delta,
                pe_delta=row.pe_delta,
            )
        )
    note = (
        "1m ATM±N via POST /marketfeed/quote. "
        + (
            f"OI fields found on {oi_found} legs."
            if oi_found
            else "DATA_INSUFFICIENT: quote payload had no OI keys we recognize (VERIFY FROM DOCS)."
        )
    )
    snap = ChainSnapshot(
        underlying=market.id,
        expiry=previous.expiry,
        spot=previous.spot,
        as_of_ist=now_ist_iso(),
        mode="strike_buildup_1m",
        dry_run=False,
        strikes=new_rows,
        source="dhan_quote_atm_wing",
        note=note,
    )
    if persist and repo_root is not None:
        save_snapshot(
            repo_root,
            settings.snapshots_dir,
            snap,
            remember_last=settings.remember_last_snapshot,
        )
    return snap


def poll_underlyings(
    cfg: WorkspaceConfig,
    client: DhanClient,
    *,
    mode: PollMode,
    persist: bool = True,
) -> list[tuple[ChainSnapshot, ChainBias]]:
    settings = cfg.desk_intel
    repo = cfg.repo_root
    quote_gate = MinIntervalGate(settings.quote_min_seconds)
    out: list[tuple[ChainSnapshot, ChainBias]] = []
    for market in cfg.markets:
        if not market.enabled:
            continue
        previous = latest_snapshot(repo, settings.snapshots_dir, market.id)
        if mode == "strike_buildup_1m":
            snap = fetch_strike_buildup_1m(
                client,
                market,
                settings,
                quote_gate=quote_gate,
                persist=persist,
                repo_root=repo,
            )
        else:
            snap = fetch_full_chain(
                client,
                market,
                settings,
                mode=mode,
                persist=persist,
                repo_root=repo,
            )
        versus = previous if previous and previous.as_of_ist != snap.as_of_ist else None
        bias = compute_chain_bias(snap, settings, versus=versus)
        out.append((snap, bias))
    return out
