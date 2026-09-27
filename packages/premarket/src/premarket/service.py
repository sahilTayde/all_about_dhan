"""Pre-market context: run every source (in parallel, under a deadline), then bias / levels / event risk.

Advisory only. Output is a JSON context plus a short markdown brief. It never places orders and
never blocks trading: a failed source is listed under `missing`, and the run still writes a file.
"""

from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

import yaml

from premarket.sources import SOURCE_TYPES, LiveFetcher, SourceContext, SourceResult

SCHEMA = "premarket-context-v1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


class ConfigError(ValueError):
    pass


def load_config(path: Optional[Path] = None) -> dict[str, Any]:
    path = Path(path or repo_root() / "config" / "premarket.yaml")
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    if not isinstance(cfg, dict):
        raise ConfigError(f"{path}: top level must be a mapping, got {type(cfg).__name__}")
    return cfg


def build_sources(market_cfg: dict[str, Any]) -> list[Any]:
    out = []
    for spec in market_cfg.get("sources") or []:
        spec = dict(spec)
        kind = spec.pop("type")
        if kind not in SOURCE_TYPES:
            raise ValueError(f"unknown source type {kind!r}; known: {sorted(SOURCE_TYPES)}")
        out.append(SOURCE_TYPES[kind](spec.pop("name"), **spec))
    return out


def _run_one(src: Any, ctx: SourceContext) -> SourceResult:
    t0 = time.perf_counter()
    try:
        res = src.fetch(ctx)
    except Exception as exc:  # noqa: BLE001 - every failure is a MISSING source, never a crash
        res = SourceResult(src.name, "MISSING", {}, f"{type(exc).__name__}: {exc}"[:300])
    res.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return res


def collect(sources: list[Any], ctx: SourceContext, deadline_s: float) -> dict[str, SourceResult]:
    """One daemon thread per source: a hung socket can neither hold the brief nor keep the process alive."""
    done: "queue.Queue[SourceResult]" = queue.Queue()
    for s in sources:
        threading.Thread(target=lambda s=s: done.put(_run_one(s, ctx)), name=f"premarket-{s.name}", daemon=True).start()
    results: dict[str, SourceResult] = {}
    end = time.monotonic() + deadline_s
    while len(results) < len(sources):
        try:
            r = done.get(timeout=max(0.0, end - time.monotonic()))
        except queue.Empty:
            break
        results[r.name] = r
    for s in sources:
        results.setdefault(s.name, SourceResult(s.name, "MISSING", {}, f"deadline {deadline_s}s exceeded"))
    return {s.name: results[s.name] for s in sources}


# ------------------------------------------------------------------ interpretation (HYPOTHESIS rules)


def metrics_from(results: dict[str, SourceResult]) -> dict[str, dict[str, Any]]:
    """Flat metric map from usable (OK) sources: quotes by key, flows as `value`."""
    out: dict[str, dict[str, Any]] = {}
    for r in results.values():
        if r.status != "OK":
            continue
        for key, q in (r.data.get("quotes") or {}).items():
            if key not in (r.data.get("stale") or []):
                out[key] = q
        for key, v in (r.data.get("flows") or {}).items():
            if key.endswith("_CR") and v is not None:
                out[key] = {"value": v}
    return out


def score_bias(metrics: dict[str, dict[str, Any]], rules: list[dict[str, Any]], min_inputs: int) -> dict[str, Any]:
    inputs, total = [], 0
    for rule in rules:
        m = metrics.get(rule["metric"])
        value = None if m is None else m.get(rule.get("field", "change_pct"))
        if value is None:
            continue
        thr = float(rule["threshold"])
        vote = int(rule["sign"]) if value >= thr else -int(rule["sign"]) if value <= -thr else 0
        total += vote
        inputs.append({"metric": rule["metric"], "field": rule.get("field", "change_pct"), "value": value, "vote": vote})
    n = len(inputs)
    if n < min_inputs:
        label, mean = "UNKNOWN", None
    else:
        mean = total / n
        label = "BULLISH" if mean >= 0.34 else "BEARISH" if mean <= -0.34 else "NEUTRAL"
    coverage = n / len(rules) if rules else 0.0
    confidence = 0.0 if mean is None else round(coverage * abs(mean), 2)
    return {"label": label, "score": total, "n_inputs": n, "n_rules": len(rules), "coverage": round(coverage, 2),
            "confidence": confidence, "inputs": inputs}


def score_event_risk(results: dict[str, SourceResult], metrics: dict[str, dict[str, Any]], cfg: dict[str, Any],
                     session_date: date, roles: dict[str, str]) -> dict[str, Any]:
    reasons: list[str] = []
    score = 0
    vix = metrics.get(str(cfg.get("vix_metric") or ""))
    if vix:
        if vix.get("price") is not None and vix["price"] >= float(cfg.get("vix_level_high", 1e9)):
            score += 2
            reasons.append(f"VIX {vix['price']} ≥ {cfg.get('vix_level_high')}")
        if vix.get("change_pct") is not None and vix["change_pct"] >= float(cfg.get("vix_change_pct_high", 1e9)):
            score += 1
            reasons.append(f"VIX {vix['change_pct']:+.1f}% vs prior close")
    news = [it for name, r in results.items() if roles.get(name) == "news" and r.status == "OK"
            for it in r.data.get("items") or []]
    for word, weight in (cfg.get("keywords") or {}).items():
        hit = next((it for it in news if re.search(rf"\b{re.escape(str(word))}\b", it["title"], re.I)), None)
        if hit:
            score += int(weight)
            reasons.append(f"headline '{word}': {hit['title'][:90]}")
    for ev in cfg.get("calendar") or []:
        if str(ev.get("date")) == session_date.isoformat():
            score += int(ev.get("weight", 2))
            reasons.append(f"calendar: {ev.get('event')}")
    have_news = any(roles.get(n) == "news" and r.status == "OK" for n, r in results.items())
    if not vix and not have_news and not reasons:
        label = "UNKNOWN"
    else:
        label = ("HIGH" if score >= int(cfg.get("high_at", 4)) else "MEDIUM" if score >= int(cfg.get("medium_at", 2))
                 else "LOW")
    return {"label": label, "score": score, "reasons": reasons}


def build_context(
    market: str = "india_index", *, config: Optional[dict[str, Any]] = None, fetcher: Any = None,
    root: Optional[Path] = None, now: Optional[datetime] = None, session_date: Optional[date] = None,
) -> dict[str, Any]:
    cfg = config if config is not None else load_config()
    mcfg = (cfg.get("markets") or {}).get(market)
    if mcfg is None:
        raise ValueError(f"unknown market {market!r}; configured: {sorted(cfg.get('markets') or {})}")
    tz = ZoneInfo(str(mcfg.get("timezone") or "UTC"))
    now = (now or datetime.now(timezone.utc)).astimezone(tz)
    session_date = session_date or now.date()
    fetcher = fetcher if fetcher is not None else LiveFetcher(float(cfg.get("timeout_s", 6)))
    ctx = SourceContext(session_date, now, Path(root or repo_root()), fetcher, float(cfg.get("stale_after_h", 96)))
    sources = build_sources(mcfg)
    results = collect(sources, ctx, float(cfg.get("deadline_s", 45)))
    roles = {s.name: str(s.params.get("role") or "") for s in sources}

    metrics = metrics_from(results)
    bias = score_bias(metrics, list(mcfg.get("bias_rules") or []), int(mcfg.get("min_bias_inputs", 3)))
    risk = score_event_risk(results, metrics, dict(mcfg.get("event_risk") or {}), session_date, roles)

    levels: dict[str, dict[str, Any]] = {u: {} for u in mcfg.get("underlyings") or []}
    for r in results.values():
        if r.status == "MISSING":
            continue
        for und, lv in (r.data.get("levels") or {}).items():
            levels.setdefault(und, {}).update(lv)
        for und, walls in (r.data.get("oi_walls") or {}).items():
            levels.setdefault(und, {})["oi_walls"] = walls
    intermarket = {k: v for r in results.values() if r.status != "MISSING" for k, v in (r.data.get("quotes") or {}).items()}
    flows = next((r.data["flows"] for r in results.values() if r.status != "MISSING" and r.data.get("flows")), {})

    def items(role: str) -> list[dict[str, Any]]:
        rows = [it for n, r in results.items() if roles.get(n) == role and r.status != "MISSING" for it in r.data.get("items") or []]
        return sorted(rows, key=lambda x: x.get("published") or "", reverse=True)[:20]

    missing = [n for n, r in results.items() if r.status == "MISSING"]
    stale = [n for n, r in results.items() if r.status == "STALE"]
    brief_by = str(mcfg.get("brief_by") or "")
    before = None
    if brief_by and session_date == now.date():
        hh, mm = (int(x) for x in brief_by.split(":"))
        before = (now.hour, now.minute) < (hh, mm)
    return {
        "schema": SCHEMA, "market": market, "session_date": session_date.isoformat(),
        "as_of": now.isoformat(timespec="seconds"), "brief_by": brief_by or None, "generated_before_brief_by": before,
        "advisory_only": True, "orders": "never", "blocks_trading": False, "layer": "HYPOTHESIS", "validated": False,
        "bias": bias, "confidence": bias["confidence"], "event_risk": risk,
        "hold_new_tickets_advice": risk["label"] == "HIGH",
        "levels": levels, "intermarket": intermarket, "flows": flows,
        "headlines": items("news"), "announcements": items("announcements"),
        "sources": {n: r.summary() for n, r in results.items()},
        "missing": missing, "stale": stale,
        "coverage": round(sum(1 for r in results.values() if r.status == "OK") / len(results), 2) if results else 0.0,
    }


# ------------------------------------------------------------------ brief + output


def _fmt(x: Any) -> str:
    return "—" if x is None else f"{x:,.2f}" if isinstance(x, float) else str(x)


def render_brief(c: dict[str, Any]) -> str:
    b, r = c["bias"], c["event_risk"]
    lines = [
        f"# Pre-market brief — {c['market']} — {c['session_date']}",
        "",
        f"_As of {c['as_of']}. Advisory only (HYPOTHESIS, not validated). Never places orders; trading does not wait for it._",
        "",
        f"- **Bias:** {b['label']} (score {b['score']:+d} from {b['n_inputs']}/{b['n_rules']} inputs, confidence {c['confidence']:.2f})",
        f"- **Event risk:** {r['label']} (score {r['score']})" + (" — advice: hold new tickets until the open settles" if c["hold_new_tickets_advice"] else ""),
    ]
    for why in r["reasons"][:5]:
        lines.append(f"  - {why}")
    if c["levels"]:
        lines += ["", "| Index | Prev H | Prev L | Prev C | Pivot | R1 | S1 | Call wall | Put wall |", "|---|---|---|---|---|---|---|---|---|"]
        for und, lv in c["levels"].items():
            pd, w = lv.get("prev_day") or {}, lv.get("oi_walls") or {}
            lines.append(f"| {und} | {_fmt(pd.get('high'))} | {_fmt(pd.get('low'))} | {_fmt(pd.get('close'))} | "
                         f"{_fmt(lv.get('pivot'))} | {_fmt(lv.get('r1'))} | {_fmt(lv.get('s1'))} | "
                         f"{_fmt(w.get('call_wall_strike'))} | {_fmt(w.get('put_wall_strike'))} |")
    if c["intermarket"]:
        lines += ["", "**Intermarket:** " + ", ".join(
            f"{k} {_fmt(v.get('price'))} ({v['change_pct']:+.2f}%)" if v.get("change_pct") is not None else f"{k} {_fmt(v.get('price'))}"
            for k, v in c["intermarket"].items())]
    if c["flows"]:
        lines.append(f"**FII/DII cash (₹ cr, {c['flows'].get('date')}):** FII {_fmt(c['flows'].get('FII_NET_CR'))}, "
                     f"DII {_fmt(c['flows'].get('DII_NET_CR'))}")
    if c["headlines"]:
        lines += ["", "**Headlines:**"] + [f"- {h['title']} ({h['source']})" for h in c["headlines"][:5]]
    lines += ["", f"**Missing sources:** {', '.join(c['missing']) or 'none'}"]
    if c["stale"]:
        lines.append(f"**Stale sources:** {', '.join(c['stale'])}")
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_outputs(c: dict[str, Any], out_dir: Path) -> dict[str, str]:
    stem = f"{c['market']}_{c['session_date']}"
    blob = json.dumps(c, indent=2, ensure_ascii=False, default=str) + "\n"
    paths = {"json": out_dir / f"{stem}.json", "brief": out_dir / f"{stem}.md", "latest": out_dir / f"{c['market']}_latest.json"}
    _atomic_write(paths["json"], blob)
    _atomic_write(paths["brief"], render_brief(c))
    _atomic_write(paths["latest"], blob)
    return {k: str(v) for k, v in paths.items()}
