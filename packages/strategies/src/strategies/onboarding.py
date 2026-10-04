"""K9 strategy onboarding checklist. Enforced in CI for every registry entry.

Checks:
- full ExitPlan with a catastrophic stop, or round-11 defaults by hash (REG-18)
- entry_policy declared (chase unless a preregistered spec says otherwise)
- preregistered forward spec + hash if the strategy leaves shadow (V2-20a)
- legacy_logic_from declared; named legacy analysts require their PR-010 REG tests
"""

from __future__ import annotations

from pathlib import Path

from contracts.payloads import ExitPlan

from .api import StrategyMeta
from .params_hash import ROUND11_DEFAULTS_SHA256, defaults_from_tag
from .registry import RegistryEntry, load_registry
from .runtime import StrategyRuntimeError, load_strategy

# PR-010 analyst bugs become REG tests only when that logic is re-implemented.
PR010_BUG_REG_TOKENS: dict[str, tuple[str, ...]] = {
    "oi": ("reversed_oi", "oi_not_reversed", "reg_oi"),
    "greeks": ("greeks_vote_intent", "greeks_not_double_counted", "reg_greeks"),
    "hold_series": ("hold_series", "reg_01"),
    "ml": ("degenerate_ml", "reg_ml"),
}

ROUND11_DEFAULTS_FROM = defaults_from_tag(ROUND11_DEFAULTS_SHA256)


def check_exit_plan(plan: object) -> list[str]:
    """REG-18 / K9: catastrophic present, or defaults_from is the round-11 hash."""
    errors: list[str] = []
    if isinstance(plan, ExitPlan):
        if plan.catastrophic is None and not _defaults_ok(plan.defaults_from):
            errors.append("REG-18d: no catastrophic stop and defaults_from is not round 11")
        return errors
    errors.append("K9: strategy has no ExitPlan")
    return errors


def _defaults_ok(tag: str | None) -> bool:
    if tag is None:
        return False
    return tag == ROUND11_DEFAULTS_FROM or tag.endswith(ROUND11_DEFAULTS_SHA256)


def check_entry(entry: RegistryEntry, instance: object, collected: list[str]) -> list[str]:
    """Return onboarding errors for one registry row."""
    errors: list[str] = []
    meta = getattr(instance, "meta", None)
    if not isinstance(meta, StrategyMeta):
        return ["K9: strategy has no StrategyMeta"]
    errors.extend(check_exit_plan(getattr(instance, "exit_plan", None)))
    if meta.entry_policy is None or not meta.entry_policy.mode:
        errors.append("K9: entry_policy is not declared")
    if meta.stage != "shadow":
        spec = Path("config/v2/forward/specs") / f"{entry.strategy_id}.yaml"
        if not spec.is_file():
            errors.append(
                f"K9: stage {meta.stage!r} requires a preregistered forward spec at {spec}"
            )
    legacy = tuple(entry.legacy_logic_from) or tuple(meta.legacy_logic_from)
    for analyst in legacy:
        tokens = PR010_BUG_REG_TOKENS.get(analyst)
        if tokens is None:
            errors.append(f"K9: unknown legacy_logic_from {analyst!r}")
            continue
        if not any(any(tok in node for tok in tokens) for node in collected):
            errors.append(f"K9: legacy_logic_from {analyst!r} has no collected PR-010 REG test")
    return errors


def check_registry(
    registry: dict[str, RegistryEntry] | None = None,
    *,
    collected_nodeids: list[str] | None = None,
) -> list[str]:
    """Check every registry entry. Empty registry is ok (no new strategies)."""
    rows = registry if registry is not None else load_registry()
    collected = collected_nodeids if collected_nodeids is not None else []
    errors: list[str] = []
    for sid, entry in rows.items():
        try:
            instance = load_strategy(sid, rows)
        except StrategyRuntimeError as exc:
            if "PENDING_LAB" in str(exc) and entry.stage == "shadow":
                continue
            errors.append(f"{sid}: load failed: {exc}")
            continue
        for item in check_entry(entry, instance, collected):
            errors.append(f"{sid}: {item}")
    return errors


def main(argv: list[str] | None = None) -> int:
    """CI entry: exit 1 if any registry entry fails K9."""
    del argv
    problems = check_registry()
    if problems:
        for line in problems:
            print(f"K9: {line}")
        return 1
    print("K9: onboarding checklist passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
