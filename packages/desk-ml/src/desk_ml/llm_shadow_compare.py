"""Daily take/skip shadow comparison. Paper files only. Never vetoes a fill.

Arms, same signals and fields, 1.5× Dhan costs:
- R3: frozen prompt under research/lab/2026-10-11_llm_judge/R3_PREREG
- R4: prompt path from config (default research/lab/2026-10-11_llm_debrief/R4/prompt.txt)
- logistic: trained only on dates strictly before the scored day
- random skip of the same count, 2000 draws

Missing R4 file is MISSING_PROMPT. Wrong hash is LOCK_MISMATCH. Never silent.
Not a promote. trade: false.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr
from desk_ml.llm_judge import (
    IST,
    PICK_DECISIONS,
    R3_REL,
    R4_PROMPT_DEFAULT,
    R4_REL,
    R4_SHA_PREFIX_DEFAULT,
    LlmJudge,
    CompleteFn,
    _num,
    load_config,
    paper_slot_ids,
)
from desk_ml.persist import code_root

log = logging.getLogger("desk_ml.llm_shadow_compare")

SCHEMA = "llm-shadow-compare-v1"
COST_MULT = 1.5
RANDOM_DRAWS = 2000
COMPARE_REL = Path("data") / "recon" / "llm_shadow_compare"
FEATURE_KEYS = (
    "bias",
    "index_vs_vwap",
    "candle_net",
    "candle_range",
    "candle_up",
    "side_ce",
    "phase_open",
    "phase_close",
    "vix",
    "vix_missing",
    "ce_change",
    "pe_change",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def r3_dir(root: Optional[Path] = None) -> Path:
    return (Path(root) if root is not None else code_root()) / R3_REL


def r4_dir(root: Optional[Path] = None) -> Path:
    return (Path(root) if root is not None else code_root()) / R4_REL


def r3_sha256(folder: Path) -> str:
    parts = []
    for name in ("prompt.txt", "schema.json", "fields.json"):
        parts.append(name.encode("utf-8") + b"\n" + (folder / name).read_bytes())
    return hashlib.sha256(b"\n".join(parts)).hexdigest()


def verify_r3_lock(root: Optional[Path] = None) -> dict[str, Any]:
    folder = r3_dir(root)
    lock_path = folder / "lock.json"
    if not lock_path.is_file():
        return {"ok": False, "status": "MISSING_LOCK", "lock_ok": False}
    try:
        lock = json.loads(_read(lock_path))
        digest = r3_sha256(folder)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": "LOCK_UNREADABLE", "lock_ok": False, "error": str(exc)[:160]}
    expected = str(lock.get("sha256") or "")
    ok = bool(expected) and expected == digest
    return {
        "ok": ok,
        "status": "ok" if ok else "LOCK_MISMATCH",
        "lock_ok": ok,
        "sha256": digest,
        "expected": expected,
        "prereg_status": lock.get("prereg_status"),
        "id": lock.get("id") or "R3",
        "trade": False,
    }


def load_r3_prompt(root: Optional[Path] = None) -> dict[str, Any]:
    check = verify_r3_lock(root)
    if not check["ok"]:
        return {**check, "prompt": None}
    folder = r3_dir(root)
    return {**check, "prompt": _read(folder / "prompt.txt").strip()}


def r4_prompt_path(
    root: Optional[Path] = None,
    *,
    cfg: Optional[Mapping[str, Any]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Path:
    """Resolve the R4 prompt file. Config/env first, then the documented drop path."""
    base = Path(root) if root is not None else code_root()
    blob = dict(cfg) if cfg is not None else load_config(base, environ)
    raw = str(blob.get("r4_prompt_path") or R4_PROMPT_DEFAULT).strip()
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path


def r4_status(
    root: Optional[Path] = None,
    *,
    cfg: Optional[Mapping[str, Any]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    """Load R4 from the configured path. Missing or wrong hash is loud, never SLOT_EMPTY."""
    base = Path(root) if root is not None else code_root()
    blob = dict(cfg) if cfg is not None else load_config(base, environ)
    path = r4_prompt_path(base, cfg=blob, environ=environ)
    expected = str(blob.get("r4_sha256_prefix") or R4_SHA_PREFIX_DEFAULT).strip().lower()
    fallback = r4_dir(base) / "prompt.txt"
    chosen = path if path.is_file() else (fallback if fallback.is_file() else path)
    note_drop = (
        f"Drop the frozen R4 prompt (sha256 prefix {expected}) at {path}. "
        "Copy from the box path research/lab/2026-10-11_llm_debrief/."
    )
    missing = {
        "status": "MISSING_PROMPT",
        "slot": "R4",
        "prompt": None,
        "path": str(path),
        "drop_path": str(path),
        "expected_sha256_prefix": expected,
        "note": note_drop,
        "ok": False,
    }
    if not chosen.is_file():
        return missing
    try:
        text = chosen.read_text(encoding="utf-8")
    except OSError as exc:
        return {**missing, "status": "MISSING_PROMPT", "error": str(exc)[:160]}
    if not text.strip():
        return {**missing, "note": f"R4 prompt at {chosen} is empty. {note_drop}"}
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if expected and not digest.startswith(expected):
        return {
            "status": "LOCK_MISMATCH",
            "slot": "R4",
            "prompt": None,
            "path": str(chosen),
            "drop_path": str(path),
            "sha256": digest,
            "expected_sha256_prefix": expected,
            "ok": False,
            "note": (
                f"R4 prompt sha256 {digest[:8]}… does not start with {expected}. "
                f"Replace the file at {chosen}."
            ),
        }
    return {
        "status": "ok",
        "slot": "R4",
        "prompt": text.strip(),
        "path": str(chosen),
        "drop_path": str(path),
        "sha256": digest,
        "expected_sha256_prefix": expected,
        "ok": True,
    }


def compare_path(root: Path, day: str) -> Path:
    return Path(root) / COMPARE_REL / f"{day}.json"


def cumulative_path(root: Path) -> Path:
    return Path(root) / COMPARE_REL / "cumulative.json"


def dhan_charges_1_5x(trade: Mapping[str, Any]) -> Optional[float]:
    """1.5× Dhan/NSE round-trip charges. None when the ticket cannot be priced."""
    existing = _num(trade.get("charges_inr"))
    if existing is not None and existing >= 0:
        return round(existing * COST_MULT, 4)
    entry = _num(trade.get("entry"))
    exit_px = _num(trade.get("exit") or trade.get("last_ltp") or trade.get("mark"))
    qty = trade.get("qty") or trade.get("quantity")
    if qty is None and trade.get("lots") is not None and trade.get("lot_size") is not None:
        try:
            qty = int(trade["lots"]) * int(trade["lot_size"])
        except (TypeError, ValueError):
            qty = None
    if entry is None or exit_px is None:
        return None
    row = groww_round_trip_charges(
        exit_premium=float(exit_px),
        entry_premium=float(entry),
        qty=int(qty) if qty is not None else None,
        filled=True,
    )
    return round(float(row["charges_inr"]) * COST_MULT, 4)


def net_at_1_5x(trade: Mapping[str, Any]) -> Optional[float]:
    charges = dhan_charges_1_5x(trade)
    if charges is None:
        return None
    gross = _num(trade.get("gross_pnl_inr") or trade.get("realized_pnl"))
    if gross is None:
        entry = _num(trade.get("entry"))
        exit_px = _num(trade.get("exit") or trade.get("last_ltp"))
        qty = trade.get("qty") or trade.get("quantity")
        if qty is None and trade.get("lots") is not None and trade.get("lot_size") is not None:
            try:
                qty = int(trade["lots"]) * int(trade["lot_size"])
            except (TypeError, ValueError):
                qty = None
        if entry is not None and exit_px is not None and qty:
            gross = round((float(exit_px) - float(entry)) * float(qty), 4)
    if gross is None:
        net = _num(trade.get("realized_pnl_inr") or trade.get("net_pnl_inr"))
        one_x = _num(trade.get("charges_inr"))
        if net is not None and one_x is not None:
            return round(net - 0.5 * one_x, 4)
        return net
    return net_pnl_inr(gross_inr=gross, charges_inr=charges)


def _feat_num(src: Any, *keys: str) -> Optional[float]:
    if not isinstance(src, Mapping):
        return None
    for key in keys:
        val = _num(src.get(key))
        if val is not None:
            return val
    return None


def feature_vector(snapshot: Mapping[str, Any], side: Any = None) -> list[float]:
    """Compact numeric features from the same pick-snapshot fields. Missing → 0 + flag."""
    market = snapshot.get("market") if isinstance(snapshot.get("market"), Mapping) else snapshot
    candles = market.get("candles_1m_15") if isinstance(market.get("candles_1m_15"), Mapping) else {}
    vs = _feat_num(market, "index_vs_vwap") or 0.0
    net = _feat_num(candles, "net") or 0.0
    rng = _feat_num(candles, "range") or 0.0
    up = _feat_num(candles, "up") or 0.0
    wing = str(side or snapshot.get("side") or "").upper()
    phase = str(market.get("phase") or snapshot.get("hhmm") or "")
    vix = _feat_num(market, "vix")
    ce = market.get("atm_ce") if isinstance(market.get("atm_ce"), Mapping) else {}
    pe = market.get("atm_pe") if isinstance(market.get("atm_pe"), Mapping) else {}
    return [
        1.0,
        float(vs),
        float(net),
        float(rng),
        float(up),
        1.0 if wing == "CE" else 0.0,
        1.0 if phase == "open" or str(snapshot.get("hhmm") or "") < "10:30" else 0.0,
        1.0 if phase == "close" or str(snapshot.get("hhmm") or "") >= "14:30" else 0.0,
        float(vix) if vix is not None else 0.0,
        1.0 if vix is None else 0.0,
        float(_feat_num(ce, "change") or 0.0),
        float(_feat_num(pe, "change") or 0.0),
    ]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _sigmoid(z: float) -> float:
    if z >= 30:
        return 1.0
    if z <= -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def fit_logit(
    rows: Sequence[Mapping[str, Any]],
    *,
    score_day: str,
    l2: float = 1.0,
    max_iter: int = 40,
) -> dict[str, Any]:
    """Walk-forward logistic. Training rows must have day < score_day. No look-ahead."""
    train = [r for r in rows if str(r.get("day") or "") < str(score_day)]
    leaked = [r for r in rows if str(r.get("day") or "") >= str(score_day)]
    X = [list(r["features"]) for r in train if r.get("features") and r.get("label") is not None]
    y = [1.0 if r.get("label") else 0.0 for r in train if r.get("features") and r.get("label") is not None]
    if len(X) < 8 or len(set(y)) < 2:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "train_n": len(X),
            "train_days": sorted({str(r.get("day")) for r in train}),
            "lookahead": False,
            "held_out_n": len(leaked),
            "weights": None,
            "note": "Need ≥8 prior-day labelled rows and both classes.",
        }
    p = len(X[0])
    w = [0.0] * p
    for _ in range(max_iter):
        preds = [_sigmoid(_dot(row, w)) for row in X]
        grad = [l2 * w[j] for j in range(p)]
        for i, row in enumerate(X):
            err = preds[i] - y[i]
            for j in range(p):
                grad[j] += row[j] * err
        hess = [[0.0] * p for _ in range(p)]
        for j in range(p):
            hess[j][j] = l2
        for i, row in enumerate(X):
            weight = preds[i] * (1.0 - preds[i])
            for a in range(p):
                for b in range(p):
                    hess[a][b] += weight * row[a] * row[b]
        try:
            step = _solve(hess, grad)
        except ValueError:
            break
        w = [w[j] - step[j] for j in range(p)]
        if max(abs(s) for s in step) < 1e-6:
            break
    return {
        "ok": True,
        "status": "ok",
        "train_n": len(X),
        "train_days": sorted({str(r.get("day")) for r in train}),
        "lookahead": False,
        "held_out_n": len(leaked),
        "weights": w,
        "feature_keys": list(FEATURE_KEYS),
    }


def _solve(matrix: Sequence[Sequence[float]], rhs: Sequence[float]) -> list[float]:
    """Gaussian elimination with partial pivot. Small p (features only)."""
    n = len(rhs)
    a = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(a[r][i]))
        if abs(a[pivot][i]) < 1e-12:
            raise ValueError("singular")
        a[i], a[pivot] = a[pivot], a[i]
        div = a[i][i]
        for j in range(i, n + 1):
            a[i][j] /= div
        for r in range(n):
            if r == i:
                continue
            fac = a[r][i]
            for j in range(i, n + 1):
                a[r][j] -= fac * a[i][j]
    return [a[i][n] for i in range(n)]


def logit_decision(model: Mapping[str, Any], features: Sequence[float], *, threshold: float = 0.5) -> str:
    if not model.get("ok") or not model.get("weights"):
        return "TAKE"
    prob = _sigmoid(_dot(features, model["weights"]))
    return "TAKE" if prob >= threshold else "SKIP"


def random_skip_nets(
    nets: Sequence[float],
    skip_n: int,
    *,
    draws: int = RANDOM_DRAWS,
    seed: int = 1,
) -> dict[str, Any]:
    """2000 draws that drop the same skip count. Reports the distribution of kept nets."""
    vals = [float(v) for v in nets]
    n = len(vals)
    skip_n = max(0, min(int(skip_n), n))
    rng = random.Random(seed)
    totals: list[float] = []
    if n == 0:
        return {
            "draws": draws,
            "skip_n": skip_n,
            "mean_net_inr": 0.0,
            "p05_net_inr": 0.0,
            "p95_net_inr": 0.0,
            "seed": seed,
        }
    for _ in range(draws):
        if skip_n == 0:
            kept = vals
        elif skip_n == n:
            kept = []
        else:
            drop = set(rng.sample(range(n), skip_n))
            kept = [vals[i] for i in range(n) if i not in drop]
        totals.append(sum(kept))
    totals.sort()
    def _pct(p: float) -> float:
        if not totals:
            return 0.0
        idx = min(len(totals) - 1, max(0, int(round((p / 100.0) * (len(totals) - 1)))))
        return round(totals[idx], 4)
    return {
        "draws": draws,
        "skip_n": skip_n,
        "mean_net_inr": round(sum(totals) / len(totals), 4),
        "p05_net_inr": _pct(5),
        "p95_net_inr": _pct(95),
        "seed": seed,
    }


def _trade_day(trade: Mapping[str, Any]) -> str:
    for key in ("day", "session_ist_date", "closed_ist", "opened_ist"):
        raw = trade.get(key)
        if raw:
            return str(raw)[:10]
    return ""


def _is_closed(trade: Mapping[str, Any]) -> bool:
    status = str(trade.get("status") or "").upper()
    if status in {"CLOSED", "FLAT"}:
        return True
    return trade.get("exit") is not None or bool(trade.get("closed_ist") or trade.get("closed_ts"))


def load_closed_trades(root: Path, *, on_day: Optional[str] = None, before_day: Optional[str] = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    board = root / "data" / "recon" / "ml_paper_dashboard.json"
    if board.is_file():
        try:
            blob = json.loads(board.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            blob = {}
        for trade in blob.get("closed_trades") or []:
            if isinstance(trade, Mapping):
                rows.append(dict(trade))
    folder = root / "data" / "recon" / "paper_closed"
    if folder.is_dir():
        for path in folder.glob("*.json"):
            try:
                blob = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            items = blob if isinstance(blob, list) else blob.get("closed_trades") or blob.get("trades") or []
            for trade in items:
                if isinstance(trade, Mapping):
                    rows.append(dict(trade))
    out = []
    seen: set[str] = set()
    for trade in rows:
        if not _is_closed(trade):
            continue
        day = _trade_day(trade)
        if on_day and day != on_day:
            continue
        if before_day and (not day or day >= before_day):
            continue
        tid = str(trade.get("trade_id") or f"{day}:{trade.get('underlying')}:{trade.get('side')}:{trade.get('entry')}")
        if tid in seen:
            continue
        seen.add(tid)
        out.append(trade)
    return out


def load_pick_rows(root: Path, day: str) -> list[dict[str, Any]]:
    path = root / "data" / "shadow" / f"{day}.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, Mapping):
            continue
        if row.get("job") != "PICK":
            continue
        out.append(dict(row))
    return out


def _match_pick(picks: Sequence[Mapping[str, Any]], trade: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    tid = str(trade.get("trade_id") or "")
    for row in picks:
        if tid and str(row.get("trade_id") or "") == tid:
            return row
    key = (
        str(trade.get("underlying") or "").upper(),
        str(trade.get("side") or ""),
        str(trade.get("book_id") or trade.get("rule_id") or trade.get("setup") or ""),
    )
    for row in picks:
        got = (
            str(row.get("underlying") or "").upper(),
            str(row.get("side") or ""),
            str(row.get("setup") or ""),
        )
        if got == key:
            return row
    return None


def labelled_rows(
    trades: Sequence[Mapping[str, Any]],
    picks: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out = []
    for trade in trades:
        net = net_at_1_5x(trade)
        if net is None:
            continue
        pick = _match_pick(picks, trade) or {}
        snapshot = pick.get("snapshot") if isinstance(pick.get("snapshot"), Mapping) else {}
        if not snapshot:
            snapshot = {
                "side": trade.get("side"),
                "hhmm": str(trade.get("opened_ist") or "")[11:16],
                "market": {
                    "phase": "open" if str(trade.get("opened_ist") or "")[11:16] < "10:30" else "mid",
                    "index_vs_vwap": trade.get("index_vs_vwap"),
                    "vix": trade.get("vix"),
                    "candles_1m_15": trade.get("candles_1m_15") or {},
                    "atm_ce": {"change": trade.get("ce_change")},
                    "atm_pe": {"change": trade.get("pe_change")},
                },
            }
        out.append(
            {
                "day": _trade_day(trade),
                "trade_id": trade.get("trade_id"),
                "features": feature_vector(snapshot, trade.get("side")),
                "label": bool(net > 0),
                "net_1_5x": net,
                "snapshot": snapshot,
                "setup": trade.get("book_id") or trade.get("rule_id") or trade.get("setup"),
                "side": trade.get("side"),
                "underlying": trade.get("underlying"),
                "trade": trade,
            }
        )
    return out


def _apply_decisions(rows: Sequence[Mapping[str, Any]], decisions: Sequence[str]) -> dict[str, Any]:
    kept = []
    skipped = []
    for row, decision in zip(rows, decisions):
        net = float(row["net_1_5x"])
        if str(decision).upper() == "SKIP":
            skipped.append(net)
        else:
            kept.append(net)
    return {
        "take_n": len(kept),
        "skip_n": len(skipped),
        "net_inr": round(sum(kept), 4),
        "skipped_net_inr": round(sum(skipped), 4),
    }


def _llm_decisions(
    rows: Sequence[Mapping[str, Any]],
    *,
    prompt: str,
    root: Path,
    complete_fn: Optional[CompleteFn],
    environ: Optional[Mapping[str, str]],
) -> tuple[list[str], dict[str, Any]]:
    cfg = {**load_config(root, environ), "pick_system": prompt}
    worker = LlmJudge(cfg, root=root, complete_fn=complete_fn, environ=environ)
    decisions: list[str] = []
    calls = 0
    skipped = 0
    try:
        for i, row in enumerate(rows):
            snap = row.get("snapshot") or {}
            verdict = worker.review("PICK", snap, dedupe_key=f"shadow-r:{row.get('trade_id') or i}")
            if verdict.get("status") == "ok" and verdict.get("decision") in PICK_DECISIONS:
                decisions.append(str(verdict["decision"]))
                calls += 1
            else:
                decisions.append("TAKE")
                skipped += 1
    finally:
        worker.close()
    return decisions, {"calls": calls, "skipped": skipped, "cost_usd": round(worker.cost_usd, 6)}


def _load_cumulative(root: Path) -> dict[str, Any]:
    path = cumulative_path(root)
    if not path.is_file():
        return {"schema": SCHEMA, "days": [], "r3_net": 0.0, "logit_net": 0.0, "random_mean": 0.0, "trade": False, "promote": False}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        blob = {}
    if not isinstance(blob, Mapping):
        blob = {}
    return dict(blob)


def _write_json(path: Path, blob: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(blob), indent=2, default=str) + "\n", encoding="utf-8")
    return path


def run_day(
    day: str,
    *,
    root: Path,
    trades: Optional[Sequence[Mapping[str, Any]]] = None,
    prior_trades: Optional[Sequence[Mapping[str, Any]]] = None,
    picks: Optional[Sequence[Mapping[str, Any]]] = None,
    complete_fn: Optional[CompleteFn] = None,
    environ: Optional[Mapping[str, str]] = None,
    seed: int = 1,
    persist: bool = True,
) -> dict[str, Any]:
    """Score one IST day. Logistic fits only on dates < day. Shadow only."""
    slots = paper_slot_ids(root, allow_code_root=False)
    day_trades = list(trades) if trades is not None else load_closed_trades(root, on_day=day)
    if slots:
        day_trades = [
            t
            for t in day_trades
            if str(t.get("book_id") or t.get("rule_id") or t.get("setup") or t.get("strategy_id") or "") in slots
            or t.get("source") == "paper_slot"
            or not slots
        ]
    prior = list(prior_trades) if prior_trades is not None else load_closed_trades(root, before_day=day)
    pick_rows = list(picks) if picks is not None else load_pick_rows(root, day)
    prior_picks: list[dict[str, Any]] = []
    if prior_trades is None:
        shadow_dir = root / "data" / "shadow"
        if shadow_dir.is_dir():
            for path in shadow_dir.glob("*.jsonl"):
                if path.stem < day:
                    prior_picks.extend(load_pick_rows(root, path.stem))
    scored = labelled_rows(day_trades, pick_rows)
    history = labelled_rows(prior, prior_picks if prior_trades is None else [])
    if prior_trades is not None:
        history = labelled_rows(prior, [])
    for row in history:
        if str(row.get("day") or "") >= day:
            raise RuntimeError("logistic training saw scored-day or future rows")
    model = fit_logit(history, score_day=day)
    r3 = load_r3_prompt(root)
    r4 = r4_status(root)
    r3_decisions: list[str] = []
    r3_meta: dict[str, Any] = {"status": r3.get("status"), "lock_ok": r3.get("lock_ok"), "prompt_version": "R3"}
    if r3.get("ok") and r3.get("prompt") and scored:
        r3_decisions, extra = _llm_decisions(
            scored, prompt=str(r3["prompt"]), root=root, complete_fn=complete_fn, environ=environ
        )
        r3_meta.update(extra)
        r3_meta["status"] = "ok"
    elif scored and not r3.get("ok"):
        r3_decisions = ["TAKE"] * len(scored)
    r4_decisions: list[str] = []
    r4_meta: dict[str, Any] = {
        "status": r4.get("status"),
        "prompt_version": "R4",
        "note": r4.get("note"),
        "path": r4.get("path") or r4.get("drop_path"),
        "drop_path": r4.get("drop_path") or r4.get("path"),
        "expected_sha256_prefix": r4.get("expected_sha256_prefix") or R4_SHA_PREFIX_DEFAULT,
        "ok": bool(r4.get("ok")),
    }
    if r4.get("status") == "ok" and r4.get("prompt") and scored:
        r4_decisions, extra = _llm_decisions(
            scored, prompt=str(r4["prompt"]), root=root, complete_fn=complete_fn, environ=environ
        )
        r4_meta.update(extra)
    logit_decisions = [logit_decision(model, row["features"]) for row in scored]
    r3_arm = _apply_decisions(scored, r3_decisions) if r3_decisions else {"take_n": 0, "skip_n": 0, "net_inr": None}
    r4_arm = _apply_decisions(scored, r4_decisions) if r4_decisions else {"take_n": 0, "skip_n": 0, "net_inr": None, "status": r4.get("status")}
    logit_arm = _apply_decisions(scored, logit_decisions) if scored else {"take_n": 0, "skip_n": 0, "net_inr": 0.0}
    skip_n = int(r3_arm.get("skip_n") or logit_arm.get("skip_n") or 0)
    nets = [float(r["net_1_5x"]) for r in scored]
    rnd = random_skip_nets(nets, skip_n, draws=RANDOM_DRAWS, seed=seed)
    plain_net = round(sum(nets), 4)
    r3_net = r3_arm.get("net_inr")
    vs_random = None if r3_net is None else round(float(r3_net) - float(rnd["mean_net_inr"]), 4)
    out = {
        "schema": SCHEMA,
        "day": day,
        "n_signals": len(scored),
        "cost_mult": COST_MULT,
        "random_draws": RANDOM_DRAWS,
        "plain_net_inr": plain_net,
        "arms": {
            "r3": {**r3_arm, **r3_meta, "lock_ok": bool(r3.get("lock_ok"))},
            "r4": {**r4_arm, **r4_meta},
            "logit": {
                **logit_arm,
                "status": model.get("status"),
                "train_n": model.get("train_n"),
                "train_days": model.get("train_days"),
                "lookahead": False,
                "held_out_n": model.get("held_out_n"),
            },
            "random": {**rnd, "status": "ok"},
        },
        "vs_random": {"r3_minus_random_mean": vs_random},
        "orders": "REFUSED",
        "promote": False,
        "shadow": True,
        "trade": False,
        "veto": False,
        "note": "Shadow compare only. 1.5× Dhan costs. Logistic trains on earlier dates only. NO_PROMOTE.",
    }
    if persist:
        _write_json(compare_path(root, day), out)
        cum = _load_cumulative(root)
        days = [d for d in (cum.get("days") or []) if str(d.get("day")) != day]
        days.append(
            {
                "day": day,
                "r3_net": r3_net,
                "logit_net": logit_arm.get("net_inr"),
                "random_mean": rnd["mean_net_inr"],
                "n_signals": len(scored),
            }
        )
        days.sort(key=lambda d: str(d.get("day")))
        cum = {
            "schema": SCHEMA,
            "as_of": datetime.now(IST).date().isoformat(),
            "days": days,
            "r3_net": round(sum(float(d["r3_net"]) for d in days if d.get("r3_net") is not None), 4),
            "logit_net": round(sum(float(d["logit_net"]) for d in days if d.get("logit_net") is not None), 4),
            "random_mean": round(sum(float(d["random_mean"]) for d in days if d.get("random_mean") is not None), 4),
            "n_days": len(days),
            "orders": "REFUSED",
            "promote": False,
            "shadow": True,
            "trade": False,
        }
        cum["r3_minus_random"] = round(float(cum["r3_net"]) - float(cum["random_mean"]), 4)
        _write_json(cumulative_path(root), cum)
        out["cumulative"] = cum
        out["path"] = str(compare_path(root, day))
    else:
        out["cumulative"] = {
            "r3_net": r3_net,
            "random_mean": rnd["mean_net_inr"],
            "r3_minus_random": vs_random,
            "n_days": 1,
        }
    return out


def _r4_public(r4: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": r4.get("status") or "MISSING_PROMPT",
        "slot": "R4",
        "ok": bool(r4.get("ok")),
        "path": r4.get("path") or r4.get("drop_path"),
        "drop_path": r4.get("drop_path") or r4.get("path"),
        "expected_sha256_prefix": r4.get("expected_sha256_prefix") or R4_SHA_PREFIX_DEFAULT,
        "sha256": (str(r4.get("sha256") or "")[:8] or None),
        "note": r4.get("note"),
    }


def load_founder_view(root: Path) -> dict[str, Any]:
    r4 = _r4_public(r4_status(root))
    path = cumulative_path(root)
    if not path.is_file():
        return {
            "schema": SCHEMA,
            "ok": False,
            "status": "NO_DATA",
            "r3_net": None,
            "random_mean": None,
            "r3_minus_random": None,
            "n_days": 0,
            "days": [],
            "r4": r4,
            "orders": "REFUSED",
            "promote": False,
            "shadow": True,
            "trade": False,
        }
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        blob = {}
    return {
        "schema": SCHEMA,
        "ok": True,
        "status": "ok",
        "r3_net": blob.get("r3_net"),
        "logit_net": blob.get("logit_net"),
        "random_mean": blob.get("random_mean"),
        "r3_minus_random": blob.get("r3_minus_random"),
        "n_days": blob.get("n_days") or len(blob.get("days") or []),
        "days": blob.get("days") or [],
        "r4": r4,
        "orders": "REFUSED",
        "promote": False,
        "shadow": True,
        "trade": False,
    }


def run_nightly(root: Path, *, day: Optional[str] = None, persist: bool = True, complete_fn: Optional[CompleteFn] = None) -> dict[str, Any]:
    stamp = day or datetime.now(IST).date().isoformat()
    try:
        return run_day(stamp, root=root, persist=persist, complete_fn=complete_fn)
    except Exception as exc:  # noqa: BLE001 — nightly parent must still finish
        log.info("llm_shadow_compare failed: %s", type(exc).__name__)
        return {
            "schema": SCHEMA,
            "ok": False,
            "day": stamp,
            "error": f"{type(exc).__name__}:{str(exc)[:160]}",
            "orders": "REFUSED",
            "promote": False,
            "shadow": True,
            "trade": False,
        }
