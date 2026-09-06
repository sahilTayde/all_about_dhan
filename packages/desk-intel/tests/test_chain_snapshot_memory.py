"""Last snapshot memory + OI/PCR/ATM CE-PE Δ vs prior poll."""

from pathlib import Path

from desk_intel.fixtures import fixture_chain, fixture_strikes
from desk_intel.option_chain_poller import compute_chain_bias
from desk_intel.schema import ChainSnapshot, StrikeRow
from desk_intel.store import last_snapshot_path, latest_snapshot, save_snapshot
from desk_intel.workspace import load_desk_workspace


def _bump_oi(rows: list[StrikeRow], *, ce: int, pe: int) -> list[StrikeRow]:
    out: list[StrikeRow] = []
    for row in rows:
        out.append(
            StrikeRow(
                strike=row.strike,
                ce_oi=row.ce_oi + ce,
                pe_oi=row.pe_oi + pe,
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
    return out


def test_yaml_default_chain_interval_is_3m() -> None:
    cfg = load_desk_workspace()
    assert cfg.desk_intel.chain_interval == "3m"
    assert cfg.desk_intel.remember_last_snapshot is True
    assert cfg.desk_intel.sentiment_windows == ["10m", "15m", "30m", "1h"]


def test_last_json_is_remembered(tmp_path: Path) -> None:
    snap = fixture_chain("NIFTY", mode="full_chain_3m")
    save_snapshot(tmp_path, "snaps", snap, remember_last=True)
    last = last_snapshot_path(tmp_path, "snaps", "NIFTY")
    assert last.is_file()
    loaded = latest_snapshot(tmp_path, "snaps", "NIFTY")
    assert loaded is not None
    assert loaded.as_of_ist == snap.as_of_ist
    assert loaded.mode in ("full_chain_3m", "full_chain_15m", "morning")


def test_oi_pcr_atm_delta_vs_last_snapshot() -> None:
    settings = load_desk_workspace().desk_intel
    first = fixture_chain("NIFTY", mode="full_chain_3m")
    first.as_of_ist = "2026-09-01T10:00:00+05:30"
    second = ChainSnapshot(
        underlying="NIFTY",
        expiry=first.expiry,
        spot=first.spot,
        as_of_ist="2026-09-01T10:03:00+05:30",
        mode="full_chain_3m",
        dry_run=True,
        strikes=_bump_oi(first.strikes, ce=5_000, pe=1_000),
        source="fixture",
        note="second poll",
    )
    bias = compute_chain_bias(second, settings, versus=first)
    assert bias.has_prior_snapshot is True
    assert bias.vs_last_as_of_ist == first.as_of_ist
    assert bias.total_ce_oi_delta == 5_000 * len(fixture_strikes(first.spot or 25000))
    assert bias.total_pe_oi_delta == 1_000 * len(fixture_strikes(first.spot or 25000))
    assert bias.pcr_oi_delta is not None
    assert any("vs last snapshot" in r for r in bias.reasons)
    # ATM row is closest to spot; both CE and PE were bumped.
    assert bias.atm_ce_buildup == 5_000
    assert bias.atm_pe_buildup == 1_000


def test_no_prior_snapshot_notes_day_oi() -> None:
    settings = load_desk_workspace().desk_intel
    snap = fixture_chain("NIFTY", mode="full_chain_3m")
    bias = compute_chain_bias(snap, settings, versus=None)
    assert bias.has_prior_snapshot is False
    assert any("no prior snapshot" in r for r in bias.reasons)
