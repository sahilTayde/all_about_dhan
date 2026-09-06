"""Option-premium books: teacher MIX vs PROJECT 007∧009. No live orders."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.algos import (
    daily_lean_at_open,
    mixed_index_veto,
    strat_001_child,
    strat_003_leans,
    strat_006_leans,
)
from backtest_engine.clocks import allow_007
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.fetch_rolling import UNDERLYINGS, fetch_rolling_range
from backtest_engine.option_sim import simulate_option_premium
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import Trade, trades_as_dicts

IST = timezone(timedelta(hours=5, minutes=30))

# 03 map: 005 ITM = CE ATM-2 / PE ATM+2; 002 OTM = CE ATM+1 / PE ATM-1
STRIKE_005_ITM = {"CE": "ATM-2", "PE": "ATM+2"}
STRIKE_ATM = {"CE": "ATM", "PE": "ATM"}
STRIKE_002_OTM = {"CE": "ATM+1", "PE": "ATM-1"}


def _log(msg: str) -> None:
    print(f"[option] {msg}", file=sys.stderr, flush=True)


def _expiry_flag(name: str) -> str:
    # 03: BANKNIFTY weekly VERIFY — prefer MONTH; NIFTY try WEEK first.
    if name == "NIFTY":
        return "WEEK"
    return "MONTH"


def _load_index_1m(client: DhanClient, years: float) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, sid, seg, inst in INDEX_YAML:
        _log(f"index 1m {name} years={years}")
        series = fetch_range(
            client,
            security_id=sid,
            exchange_segment=seg,
            instrument=inst,
            interval=1,
            years=years,
        )
        bars_1m = series.get("bars") or []
        bars_3m = resample(bars_1m, 3)
        leans = strat_003_leans(bars_3m, equal_weight_vwap=True)
        out[name] = {
            "bars_1m": bars_1m,
            "bars_3m": bars_3m,
            "leans_003": leans,
            "meta": {k: v for k, v in series.items() if k != "bars"},
        }
    daily = {n: daily_lean_at_open(out[n]["bars_3m"], out[n]["leans_003"]) for n in out}
    veto = mixed_index_veto(daily)
    return {"underlyings": out, "veto_008": veto}


def _opt_tf(bars: list, minutes: int) -> list:
    if not bars:
        return []
    return resample(bars, minutes) if minutes > 1 else list(bars)


def _rolling_pair(
    client: DhanClient,
    *,
    name: str,
    sid: str,
    seg: str,
    strike_map: dict[str, str],
    years: float,
    interval: int,
) -> tuple[list, list, dict]:
    flag = _expiry_flag(name)
    _log(f"rolling {name} CE {strike_map['CE']} {flag}")
    ce = fetch_rolling_range(
        client,
        security_id=sid,
        exchange_segment=seg,
        strike=strike_map["CE"],
        option_type="CALL",
        interval=interval,
        years=years,
        expiry_flag=flag,
    )
    thin = ce.get("bar_count", 0) < 200 or ce.get("error_count", 0) > 4
    if thin and flag == "WEEK":
        flag = "MONTH"
        _log(f"rolling {name} WEEK thin — retry MONTH")
        ce = fetch_rolling_range(
            client,
            security_id=sid,
            exchange_segment=seg,
            strike=strike_map["CE"],
            option_type="CALL",
            interval=interval,
            years=years,
            expiry_flag=flag,
        )
    _log(f"rolling {name} PE {strike_map['PE']} {flag}")
    pe = fetch_rolling_range(
        client,
        security_id=sid,
        exchange_segment=seg,
        strike=strike_map["PE"],
        option_type="PUT",
        interval=interval,
        years=years,
        expiry_flag=flag,
    )
    meta = {
        "ce": {k: v for k, v in ce.items() if k != "bars"},
        "pe": {k: v for k, v in pe.items() if k != "bars"},
        "expiry_flag_used": flag,
    }
    return ce.get("bars") or [], pe.get("bars") or [], meta


def _row(book_id: str, trades: list[Trade], extra: dict) -> dict:
    rating = rate_trades(trades, book_id=book_id)
    rating.update(extra)
    rating["pnl_unit"] = "OPTION_PREMIUM_POINTS"
    rating["option_pnl"] = rating.get("all", {}).get("sum_pts")
    rating["trade_count"] = len(trades)
    rating["trade_sample"] = trades_as_dicts(trades[:6])
    rating["costs"] = "UNKNOWN"
    rating["expectancy_label"] = "OPTIMISTIC"
    rating["promote"] = False
    rating["validated"] = False
    if rating.get("rating") == "CANDIDATE":
        # 02: costs UNKNOWN → cannot CANDIDATE / promote on optimistic premium.
        rating["rating"] = "WEAK"
        rating["reason"] = (
            (rating.get("reason") or "")
            + " Costs UNKNOWN — capped at WEAK / UNVALIDATED. Not a promote."
        )
    r = rating.get("reason") or ""
    rating["reason"] = r.replace("proxy fills (not option costs)", "option premium (costs UNKNOWN)")
    rating["reason"] = rating["reason"].replace("OOS proxy", "OOS option premium")
    return rating


def run_option_premium(
    client: DhanClient, *, years: float = 5.0, interval: int = 1
) -> dict[str, Any]:
    index = _load_index_1m(client, years)
    veto = index["veto_008"]
    books: list[dict] = []
    roll_meta: dict[str, Any] = {}
    for name, sid, seg in UNDERLYINGS:
        pack = index["underlyings"][name]
        bars_1m = pack["bars_1m"]
        bars_3m = pack["bars_3m"]
        leans_003 = pack["leans_003"]
        allow_007_3m = [allow_007(b.ts) for b in bars_3m]

        ce_itm, pe_itm, meta_itm = _rolling_pair(
            client,
            name=name,
            sid=sid,
            seg=seg,
            strike_map=STRIKE_005_ITM,
            years=years,
            interval=interval,
        )
        ce_atm, pe_atm, meta_atm = _rolling_pair(
            client,
            name=name,
            sid=sid,
            seg=seg,
            strike_map=STRIKE_ATM,
            years=years,
            interval=interval,
        )
        ce_otm, pe_otm, meta_otm = _rolling_pair(
            client,
            name=name,
            sid=sid,
            seg=seg,
            strike_map=STRIKE_002_OTM,
            years=years,
            interval=interval,
        )
        roll_meta[f"{name}/005_ITM"] = meta_itm
        roll_meta[f"{name}/ATM"] = meta_atm
        roll_meta[f"{name}/002_OTM"] = meta_otm
        _log(
            f"simulate {name} ce_itm={len(ce_itm)} pe_itm={len(pe_itm)} "
            f"ce_atm={len(ce_atm)} pe_atm={len(pe_atm)} "
            f"ce_otm={len(ce_otm)} pe_otm={len(pe_otm)}"
        )

        ce_itm_3, pe_itm_3 = _opt_tf(ce_itm, 3), _opt_tf(pe_itm, 3)
        ce_atm_3, pe_atm_3 = _opt_tf(ce_atm, 3), _opt_tf(pe_atm, 3)
        ce_otm_5, pe_otm_5 = _opt_tf(ce_otm, 5), _opt_tf(pe_otm, 5)
        ce_itm_2, pe_itm_2 = _opt_tf(ce_itm, 2), _opt_tf(pe_itm, 2)

        extra_gokul = {
            "underlying": name,
            "tape": "OPTIDX_ROLLING",
            "origin": "DHAN-DERIVED",
            "signal_tf": "3m_INDEX_resample",
        }
        for strike_name, ce, pe, smap in (
            ("005_ITM", ce_itm_3, pe_itm_3, STRIKE_005_ITM),
            ("ATM", ce_atm_3, pe_atm_3, STRIKE_ATM),
        ):
            extra = {**extra_gokul, "strike_map": smap}
            # 02 first premium charter: 009 only, no 007, no 008
            books.append(
                _row(
                    f"MIX-GOKUL-003-009/{name}/{strike_name}",
                    simulate_option_premium(
                        bars_3m,
                        leans_003,
                        ce,
                        pe,
                        strategy_id="MIX-GOKUL-003-009",
                        underlying=name,
                        use_009=True,
                        use_007_allow=None,
                        veto_sessions=None,
                    ),
                    {**extra, "filters": ["009"], "not_attached": ["007", "008"]},
                )
            )
            # 01 teacher club: 008 + 009, not 007
            books.append(
                _row(
                    f"MIX-GOKUL-003/{name}/{strike_name}",
                    simulate_option_premium(
                        bars_3m,
                        leans_003,
                        ce,
                        pe,
                        strategy_id="MIX-GOKUL-003",
                        underlying=name,
                        use_009=True,
                        use_007_allow=None,
                        veto_sessions=veto,
                    ),
                    {**extra, "filters": ["008", "009"], "not_attached": ["007"]},
                )
            )
            # PROJECT default: 007 ∧ 009 + 008
            books.append(
                _row(
                    f"MIX-DEFAULT-BUY/{name}/{strike_name}",
                    simulate_option_premium(
                        bars_3m,
                        leans_003,
                        ce,
                        pe,
                        strategy_id="MIX-DEFAULT-BUY",
                        underlying=name,
                        use_009=True,
                        use_007_allow=allow_007_3m,
                        veto_sessions=veto,
                    ),
                    {
                        **extra,
                        "origin": "PROJECT_MIX",
                        "filters": ["007", "008", "009"],
                    },
                )
            )

        child, leans_001 = strat_001_child(bars_1m)
        allow_001 = [allow_007(b.ts) for b in child]
        books.append(
            _row(
                f"MIX-HAUS-001/{name}/002_OTM",
                simulate_option_premium(
                    child,
                    leans_001,
                    ce_otm_5,
                    pe_otm_5,
                    strategy_id="MIX-HAUS-001",
                    underlying=name,
                    use_009=False,
                    use_007_allow=allow_001,
                    veto_sessions=None,
                ),
                {
                    "underlying": name,
                    "tape": "OPTIDX_ROLLING",
                    "strike_map": STRIKE_002_OTM,
                    "origin": "DHAN-DERIVED-speaker / PROJECT index universe",
                    "filters": ["007"],
                    "not_attached": ["003", "005", "009"],
                    "signal_tf": "5m_INDEX_resample",
                },
            )
        )

        bars_2m, leans_006 = strat_006_leans(bars_1m)
        books.append(
            _row(
                f"MIX-MUKUL-006/{name}/005_ITM",
                simulate_option_premium(
                    bars_2m,
                    leans_006,
                    ce_itm_2,
                    pe_itm_2,
                    strategy_id="MIX-MUKUL-006",
                    underlying=name,
                    use_009=False,
                    use_007_allow=None,
                    veto_sessions=None,
                ),
                {
                    "underlying": name,
                    "tape": "OPTIDX_ROLLING",
                    "strike_map": STRIKE_005_ITM,
                    "origin": "DHAN-DERIVED",
                    "filters": [],
                    "not_attached": ["001", "002", "003", "005", "007", "009"],
                    "alias_in_04": "MIX-SCALP-006",
                    "signal_tf": "2m_INDEX_resample",
                    "strike_note": "006 spoken ITM 100-200 pts; rolling ATM-2/ATM+2 proxy (not delta)",
                    "vix_filter": "DATA_INSUFFICIENT",
                },
            )
        )

    slim = []
    for b in books:
        slim.append(
            {
                "book_id": b.get("book_id"),
                "rating": b.get("rating"),
                "reason": b.get("reason"),
                "underlying": b.get("underlying"),
                "trade_count": b.get("trade_count"),
                "is": b.get("is"),
                "oos": b.get("oos"),
                "all": b.get("all"),
                "filters": b.get("filters"),
                "strike_map": b.get("strike_map"),
                "origin": b.get("origin"),
            }
        )
    report = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "years_requested": years,
        "option_interval": interval,
        "metrics_claimed": False,
        "research_ready_for_programming": False,
        "keep_current_strategy": True,
        "promote": False,
        "pnl_unit": "OPTION_PREMIUM_POINTS",
        "costs": "UNKNOWN",
        "news_filter": "DATA_INSUFFICIENT",
        "veto_008_days": len(veto),
        "rolling_meta": roll_meta,
        "index_meta": {n: v["meta"] for n, v in index["underlyings"].items()},
        "books_summary": slim,
        "books": books,
        "note": (
            "Long option premium (CE and PE). MIX-GOKUL-003-009 is 02 first charter "
            "(009 only). MIX-GOKUL-003 is 01 teacher club (008+009, not 007). "
            "MIX-DEFAULT-BUY is PROJECT 007∧009. MIX-HAUS-001 / MIX-MUKUL-006 are "
            "separate teacher clubs. ATM vs 2-ITM grid; 002 never on 003. "
            "Expectancy OPTIMISTIC. Not a promote."
        ),
    }
    out = repo_root() / "data" / "recon"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"BACKTEST_OPTION_{datetime.now(IST).date().isoformat()}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    report["wrote"] = str(path)
    return report
