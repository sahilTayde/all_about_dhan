"""Fixture 1m INDEX+CE+PE triples → KMeans regimes + IsolationForest overlay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from desk_ml.features import Triple, build_feature_rows
from desk_ml.fit import fit_from_rows, fit_underlying, score_features_dict, score_last
from desk_ml.model import IsolationForest, KMeans, StandardScaler, name_clusters, premium_divergence_pattern
from desk_ml.persist import load_bundle, unpack_estimators
from desk_ml.tape import labels_from_paper_ledger, load_triples

IST = timezone(timedelta(hours=5, minutes=30))


def _ts(i: int) -> int:
    return int(datetime(2026, 9, 11, 9, 15, tzinfo=IST).timestamp()) + i * 60


def _triples() -> list[Triple]:
    out: list[Triple] = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    n = 0

    def push(di: float, dce: float, dpe: float, count: int) -> None:
        nonlocal idx, ce, pe, n
        for _ in range(count):
            idx += di
            ce = max(5.0, ce + dce)
            pe = max(5.0, pe + dpe)
            out.append(Triple(ts=_ts(n), idx_close=idx, ce_close=ce, pe_close=pe))
            n += 1

    push(8.0, 1.6, -1.2, 40)
    push(-8.0, -1.5, 1.7, 40)
    push(0.2, 0.05, -0.04, 40)
    push(-10.0, -0.2, -1.8, 24)
    return out


def test_feature_builder_drops_first_bar() -> None:
    rows = build_feature_rows(_triples())
    assert len(rows) == len(_triples()) - 1


def test_kmeans_names_four_regimes() -> None:
    fitted = fit_from_rows(build_feature_rows(_triples()), seed=14)
    assert set(fitted["cluster_sizes"]) == {"TREND_UP", "TREND_DN", "RANGE", "DIVERGE"}
    assert "win_rate" not in fitted


def test_diverge_last_bar_holds() -> None:
    report = fit_underlying("NIFTY", persist=False, triples=_triples())
    assert report["ok"] is True
    assert report["promote"] is False
    assert report["win_rate"] is None
    assert report["cluster_sizes"]["DIVERGE"] >= 1


def test_fit_persist_and_score_overlay(tmp_path: Path) -> None:
    triples = _triples()
    report = fit_underlying("NIFTY", root=tmp_path, persist=True, triples=triples)
    assert report["production_params_written"] is False
    bundle = load_bundle(Path(report["path"]))
    scaler, kmeans, labels, forest = unpack_estimators(bundle)
    assert set(labels.values()) == {"TREND_UP", "TREND_DN", "RANGE", "DIVERGE"}
    scored = score_last("NIFTY", root=tmp_path, triples=triples)
    assert scored["ok"] is True
    assert scored["promote"] is False
    assert scored["execution"] == "refused"
    assert scored["llm"] is False
    assert scored["overlay"] == "HOLD"
    assert scored["allow_new_paper_ce_pe"] is False
    assert score_features_dict(scored["features"], bundle)["overlay"] == "HOLD"
    assert kmeans.k == 4
    assert forest.trees


def test_premium_divergence_rule() -> None:
    assert premium_divergence_pattern(-0.002, -0.001, -0.003) is True
    assert premium_divergence_pattern(-0.002, -0.001, 0.004) is False
    assert premium_divergence_pattern(0.002, -0.001, -0.001) is True
    assert premium_divergence_pattern(0.002, 0.003, -0.002) is False


def test_isolation_forest_ranks_extreme_higher() -> None:
    rng_rows = [[0.0, 0.0, 0.0, 0.0, 0.0] for _ in range(40)]
    extreme = [[4.0, -3.0, -3.0, 2.0, 5.0]]
    forest = IsolationForest(n_trees=20, sample_size=32, contamination=0.1, seed=3).fit(rng_rows + extreme)
    scores = forest.anomaly_scores(rng_rows + extreme)
    assert scores[-1] >= min(scores[:40])


def test_name_clusters_unique() -> None:
    cents = [
        [0.02, 0.03, -0.02, 0.01, 0.0],
        [-0.02, -0.02, 0.03, -0.01, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0],
        [0.01, -0.02, -0.03, 0.0, 0.2],
    ]
    mapping = name_clusters(cents)
    assert mapping[3] == "DIVERGE"
    assert mapping[0] == "TREND_UP"


def test_kmeans_too_few_rows() -> None:
    try:
        KMeans(k=4, seed=1).fit([[0.0] * 5] * 3)
        assert False
    except ValueError as exc:
        assert "DATA_INSUFFICIENT" in str(exc)


def test_scaler_roundtrip() -> None:
    X = [[1.0, 2.0, 3.0, 4.0, 5.0], [3.0, 2.0, 1.0, 0.0, -1.0]]
    sc = StandardScaler.fit(X)
    assert abs(sc.inverse(sc.transform(X)[0])[0] - 1.0) < 1e-9


def test_supervised_empty_ledger(tmp_path: Path) -> None:
    out = labels_from_paper_ledger(tmp_path, min_rows=50)
    assert out["status"] == "DATA_INSUFFICIENT"


def test_load_triples_missing_cache(tmp_path: Path) -> None:
    triples, meta = load_triples("NIFTY", root=tmp_path)
    assert triples == []
    assert "DATA_INSUFFICIENT" in meta["data_gaps"][0]


def test_tape_join_from_files(tmp_path: Path) -> None:
    import json

    ohlc = tmp_path / "data" / "recon" / "ohlc"
    tape = tmp_path / "data" / "recon" / "premium_tape"
    ohlc.mkdir(parents=True)
    tape.mkdir(parents=True)
    ts = [_ts(i) for i in range(5)]
    chart = {
        "timestamp": ts,
        "open": [25000 + i for i in range(5)],
        "high": [25001 + i for i in range(5)],
        "low": [24999 + i for i in range(5)],
        "close": [25000 + i * 2 for i in range(5)],
        "volume": [1] * 5,
    }
    (ohlc / "INDEX_IDX_I_13_1_2026-09-11_2026-09-11.json").write_text(json.dumps(chart))
    payload = {
        "ce": [{"ts": t, "open": 100, "high": 101, "low": 99, "close": 100 + i, "volume": 1} for i, t in enumerate(ts)],
        "pe": [{"ts": t, "open": 90, "high": 91, "low": 89, "close": 90 - i * 0.5, "volume": 1} for i, t in enumerate(ts)],
    }
    (tape / "NIFTY_ATM_1m_2026-09-11.json").write_text(json.dumps(payload))
    triples, meta = load_triples("NIFTY", root=tmp_path)
    assert meta["aligned_triples"] == 5
    assert triples[-1].ce_close == 104
