"""REG-13: changing strike-router rules changes rule_version (V2-06b)."""

from __future__ import annotations

from copy import deepcopy

from strategies.strikes import load_router_rules, rule_version


def test_reg_13_changing_router_rules_changes_rule_version() -> None:
    base = load_router_rules()
    v0 = rule_version(base)
    edited = deepcopy(base)
    edited["rules"] = dict(edited["rules"])
    edited["rules"]["dte"] = dict(edited["rules"]["dte"])
    edited["rules"]["dte"]["ge_2"] = "ITM200"
    v1 = rule_version(edited)
    assert v0 != v1
    assert v0.startswith("router-1.0.0+")
    assert v1.startswith("router-1.0.0+")

    edited["rules"]["atm_max_hold_s"] = 120
    assert rule_version(edited) != v1
