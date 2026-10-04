"""Founder-approved paper/shadow basket for V2 journals (V2-27).

Dated YAML / K6 JSON first, then ``approved_paper_shadow.yaml``.
No basket → no trades. Live stages refuse. TEST-CROSS is dry-run only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from strategies.api import SessionContext
from strategies.params_hash import ExitPlanLoadError, defaults_from_tag, load_exit_defaults
from strategies.registry import (
    INDIA_MARKET,
    Basket,
    BasketEntry,
    RegistryEntry,
    load_basket,
    load_registry,
    make_basket,
)
from strategies.runtime import HealthAlert, LoadedStrategy, StrategyRuntimeError, load_strategy

from shadow.safety import ShadowSafetyError, closed

PAPER_SHADOW_STAGES = frozenset({"shadow", "paper"})
LIVE_STAGES = frozenset({"live", "live_eligible", "limited_live", "dhan"})
TEST_CROSS_ID = "TEST-CROSS"
KIND_APPROVED = "approved_paper_shadow"
KIND_DRY_RUN = "dry_run"
KIND_DATED = "dated"
KIND_AUTO = "auto"

REASON_NO_BASKET = "NO_BASKET"
REASON_EMPTY_BASKET = "EMPTY_BASKET"
REASON_NO_REGISTRY = "NO_REGISTRY"
REASON_EXIT_DEFAULTS_MISSING = "EXIT_DEFAULTS_MISSING"
REASON_LIVE_STAGE = "LIVE_STAGE_REFUSED"
REASON_TEST_CROSS = "TEST_CROSS_FORBIDDEN"
REASON_PENDING_LAB = "PENDING_LAB"
REASON_STRATEGY_REFUSED = "STRATEGY_REFUSED"
REASON_PLUGIN_ABSTAIN = "PLUGIN_ABSTAIN"
REASON_NO_CLOSED_BAR = "NO_CLOSED_BAR"
REASON_CONFLICT = "CONFLICT"


def repo_root(start: Path | None = None) -> Path:
    here = start if start is not None else Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "config" / "v2").is_dir() and (candidate / "AGENT.md").is_file():
            return candidate
    return Path.cwd()


@dataclass(frozen=True)
class BasketPaths:
    repo: Path
    registry: Path
    exits: Path
    baskets_dir: Path
    approved: Path
    dry_run: Path


def v2_paths(repo: Path | None = None) -> BasketPaths:
    root = repo if repo is not None else repo_root()
    v2 = root / "config" / "v2"
    baskets = v2 / "baskets"
    return BasketPaths(
        repo=root,
        registry=v2 / "strategies" / "registry.yaml",
        exits=v2 / "exits" / "defaults.yaml",
        baskets_dir=baskets,
        approved=baskets / "approved_paper_shadow.yaml",
        dry_run=baskets / "dry_run.yaml",
    )


@dataclass
class LoadedBasket:
    """Session basket plus exit-default hash. Never a broker."""

    basket: Basket
    kind: str
    registry: dict[str, RegistryEntry]
    loaded: dict[str, LoadedStrategy]
    alerts: list[HealthAlert] = field(default_factory=list)
    exit_defaults: dict[str, Any] = field(default_factory=dict)
    defaults_sha256: str = ""
    defaults_from: str = ""

    @property
    def enabled_ids(self) -> tuple[str, ...]:
        return tuple(sid for sid, row in self.loaded.items() if row.enabled and row.strategy is not None)

    def refuse_reason(self) -> str | None:
        if not self.basket.entries:
            return REASON_EMPTY_BASKET
        if self.enabled_ids:
            return None
        reasons = [row.disabled_reason or REASON_STRATEGY_REFUSED for row in self.loaded.values()]
        if any(REASON_PENDING_LAB in (reason or "") for reason in reasons):
            return REASON_PENDING_LAB
        return REASON_STRATEGY_REFUSED

    def refuse_detail(self) -> str:
        parts = [
            f"{sid}:{row.disabled_reason}"
            for sid, row in self.loaded.items()
            if not row.enabled and row.disabled_reason
        ]
        return ";".join(parts)


def _entries_from_raw(raw: object) -> tuple[BasketEntry, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[BasketEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        underlyings = item.get("underlyings") or item.get("underlying") or ()
        if isinstance(underlyings, str):
            underlyings = (underlyings,)
        out.append(
            BasketEntry(
                strategy_id=str(item["strategy_id"]),
                underlyings=tuple(str(u) for u in underlyings),
                weight=float(item.get("weight", 1.0)),
                max_lots=int(item.get("max_lots", 1)),
                stage=str(item.get("stage", "shadow")),
            )
        )
    return tuple(out)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    import yaml  # type: ignore[import-untyped]

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise closed(REASON_NO_BASKET)
    return data


def _basket_from_file(path: Path, session: str, market: str) -> tuple[Basket, str]:
    data = _load_yaml_mapping(path)
    kind = str(data.get("kind") or KIND_DATED)
    file_market = data.get("market")
    if file_market is not None and str(file_market) != market:
        raise closed(REASON_NO_BASKET)
    if kind == KIND_DATED:
        file_session = data.get("session")
        if file_session is not None and str(file_session) != session:
            raise closed(REASON_NO_BASKET)
    entries = _entries_from_raw(data.get("entries"))
    return make_basket(session, market, entries, source=f"{kind}:{path.name}"), kind


def _assert_paper_shadow_basket(basket: Basket, kind: str) -> None:
    if not basket.entries:
        raise closed(REASON_EMPTY_BASKET)
    for entry in basket.entries:
        stage = (entry.stage or "").strip().lower()
        if stage in LIVE_STAGES:
            raise ShadowSafetyError(f"V2 shadow fail-closed: {entry.strategy_id} stage {entry.stage!r} is live")
        if stage not in PAPER_SHADOW_STAGES:
            raise ShadowSafetyError(
                f"V2 shadow fail-closed: {entry.strategy_id} stage {entry.stage!r} is not paper/shadow"
            )
        if entry.strategy_id == TEST_CROSS_ID and kind != KIND_DRY_RUN:
            raise ShadowSafetyError(f"V2 shadow fail-closed: {TEST_CROSS_ID} is dry-run only (never a real basket)")


def _load_defaults(path: Path) -> tuple[dict[str, Any], str, str]:
    if not path.is_file():
        raise closed(REASON_EXIT_DEFAULTS_MISSING)
    try:
        defaults, digest = load_exit_defaults(path)
    except (OSError, ExitPlanLoadError) as exc:
        raise closed(REASON_EXIT_DEFAULTS_MISSING) from exc
    return defaults, digest, defaults_from_tag(digest)


def resolve_basket(
    *,
    session: str,
    kind: str = KIND_AUTO,
    basket_path: Path | None = None,
    paths: BasketPaths | None = None,
    market: str = INDIA_MARKET,
) -> tuple[Basket, str]:
    """Dated/JSON → approved fallback. Explicit path wins. Fail closed if none."""
    loc = paths if paths is not None else v2_paths()
    cleaned = (kind or KIND_AUTO).strip().lower()
    if basket_path is not None:
        return _basket_from_file(basket_path, session, market)
    if cleaned == KIND_DRY_RUN:
        if not loc.dry_run.is_file():
            raise closed(REASON_NO_BASKET)
        return _basket_from_file(loc.dry_run, session, market)
    if cleaned == KIND_APPROVED:
        if not loc.approved.is_file():
            raise closed(REASON_NO_BASKET)
        return _basket_from_file(loc.approved, session, market)
    if cleaned != KIND_AUTO:
        raise ShadowSafetyError(f"V2 shadow fail-closed: basket kind {kind!r} is not paper/shadow")
    day = date.fromisoformat(session)
    dated = loc.baskets_dir / f"{session}.yaml"
    json_india = loc.baskets_dir / "basket_india.json"
    if dated.is_file() or json_india.is_file():
        found = load_basket(day, market, config_dir=loc.baskets_dir)
        if found is not None and found.entries:
            return found, KIND_DATED
    if loc.approved.is_file():
        return _basket_from_file(loc.approved, session, market)
    raise closed(REASON_NO_BASKET)


def load_session_basket(
    *,
    session: str,
    kind: str = KIND_AUTO,
    basket_path: Path | None = None,
    paths: BasketPaths | None = None,
    market: str = INDIA_MARKET,
) -> LoadedBasket:
    """Load registry + exit defaults + paper/shadow basket. No live path."""
    loc = paths if paths is not None else v2_paths()
    if not loc.registry.is_file():
        raise closed(REASON_NO_REGISTRY)
    defaults, digest, tag = _load_defaults(loc.exits)
    basket, resolved_kind = resolve_basket(
        session=session, kind=kind, basket_path=basket_path, paths=loc, market=market
    )
    _assert_paper_shadow_basket(basket, resolved_kind)
    registry = load_registry(loc.registry)
    if not registry:
        raise closed(REASON_NO_REGISTRY)
    loaded: dict[str, LoadedStrategy] = {}
    alerts: list[HealthAlert] = []
    for entry in basket.entries:
        sid = entry.strategy_id
        try:
            instance = load_strategy(sid, registry, required_market=market)
            start = getattr(instance, "on_session_start", None)
            if callable(start):
                start(SessionContext(session_date=session, market=market, config={}))
            loaded[sid] = LoadedStrategy(strategy=instance, registry_entry=registry.get(sid), enabled=True)
        except StrategyRuntimeError as exc:
            reason = str(exc)
            loaded[sid] = LoadedStrategy(
                strategy=None,
                registry_entry=registry.get(sid),
                enabled=False,
                disabled_reason=reason,
            )
            alerts.append(HealthAlert(kind="STRATEGY_REFUSED", strategy_id=sid, reason=reason))
    return LoadedBasket(
        basket=basket,
        kind=resolved_kind,
        registry=registry,
        loaded=loaded,
        alerts=alerts,
        exit_defaults=defaults,
        defaults_sha256=digest,
        defaults_from=tag,
    )
