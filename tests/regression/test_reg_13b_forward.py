"""REG-13b: the forward harness refuses a spec whose exit params differ from the lock."""

from __future__ import annotations

from pathlib import Path

import yaml
from strategies.forward.spec import (
    SpecRefused,
    compute_lock_digest,
    exit_params_hash,
    load_spec,
    plugin_source,
    verify_lock,
)

PLUGIN = "strategies.plugins.test_cross"


def _spec(tmp_path: Path, *, flat: str = "15:15") -> Path:
    body = {
        "spec_id": "FWD-REG13B",
        "strategy_id": "TEST-CROSS",
        "plugin": PLUGIN,
        "params": {
            "exit_plan": {"catastrophic": {"max_loss": 30000}, "flat_by_ist": flat},
        },
        "coefficients": {},
    }
    path = tmp_path / "reg13b.yaml"
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    return path


def test_reg_13b_changed_exit_param_refused(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path)
    spec = load_spec(spec_path)
    digest = compute_lock_digest(
        spec.raw, plugin_source(spec.plugin), spec.coefficients
    )
    lock = {
        "cumulative_trials": 4621,
        "specs": {
            "FWD-REG13B": {
                "sha256": digest,
                "exit_sha256": exit_params_hash(spec.params),
            }
        },
    }
    assert verify_lock(spec, lock) == digest

    edited = _spec(tmp_path, flat="15:20")
    changed = load_spec(edited)
    try:
        verify_lock(changed, lock)
        raise AssertionError("REG-13b: changed exit param must be refused")
    except SpecRefused as exc:
        assert "hash mismatch" in str(exc) or "REG-13b" in str(exc)

    # Even if the full digest is rewritten, a drifted exit hash is refused.
    lock["specs"]["FWD-REG13B"]["sha256"] = compute_lock_digest(
        changed.raw, plugin_source(changed.plugin), changed.coefficients
    )
    try:
        verify_lock(changed, lock)
        raise AssertionError("REG-13b: exit_sha256 drift must be refused")
    except SpecRefused as exc:
        assert "REG-13b" in str(exc)
