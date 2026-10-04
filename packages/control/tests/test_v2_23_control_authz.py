"""V2-23: control fails closed on customer / refresh / missing 2FA. Paper path unchanged."""

from __future__ import annotations

from pathlib import Path

from helpers import make_handler

from control.authz import authorize_command, decision_from_raw, refuse_if_auth_present


def test_control_authz_fail_closed() -> None:
    assert authorize_command(None) is None
    assert authorize_command(None, required=True) == "unauthorized"
    customer = decision_from_raw({"ok": True, "role": "customer", "sub": "c1", "typ": "access"})
    assert authorize_command(customer, "KILL", required=True) == "founder_only"
    refresh = decision_from_raw({"ok": True, "role": "founder", "sub": "founder", "typ": "refresh", "tfa": True})
    assert authorize_command(refresh, "KILL") == "refresh_forbidden"
    no_tfa = decision_from_raw({"ok": True, "role": "founder", "sub": "founder", "typ": "access"})
    assert authorize_command(no_tfa, "START") == "tfa_required"
    ok = decision_from_raw({"ok": True, "role": "founder", "sub": "founder", "typ": "access", "tfa": True})
    assert authorize_command(ok, "KILL") is None


def test_handler_rejects_auth_payload_fail_closed(tmp_path: Path) -> None:
    handler = make_handler(tmp_path)
    paper = handler.apply(
        {
            "kind": "START",
            "args": {},
            "actor": "founder",
            "reason": "paper",
            "command_id": "paper-1",
            "available_ts": handler.clock.now().isoformat(),
        }
    )
    assert paper["status"] == "applied"
    denied = handler.apply(
        {
            "kind": "START",
            "args": {},
            "actor": "founder",
            "reason": "jwt",
            "command_id": "jwt-1",
            "available_ts": handler.clock.now().isoformat(),
            "auth": {"ok": True, "role": "customer", "sub": "c1", "typ": "access"},
        }
    )
    assert denied["status"] == "rejected"
    assert denied["status_reason"] == "founder_only"
    assert refuse_if_auth_present({"kind": "KILL"}) is None
