"""C5-02: issue pair, 5-customer cap, login CLI, empty secret, refresh-as-access."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auth import (
    ACCESS_TTL_S,
    CUSTOMER_CHANNELS,
    PAPER_CUSTOMER_CAP,
    PAPER_IDENTITY_CAP,
    AuthClosed,
    authorize_control,
    issue_pair,
    load_jwt_secret,
    login,
    paper_customer_allowlist,
    refresh_session,
    require_jwt_secret,
    totp_at,
    verify_access,
)
from auth.__main__ import main as auth_main

JWT = "paper-test-hmac-not-a-production-key"
RFC_SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
NOW = 1_700_000_000.0


def test_issue_pair_customer_signals_public_only() -> None:
    pair = issue_pair(JWT, role="customer", sub="c1", now=NOW)
    access = verify_access(pair.access, JWT, NOW)
    assert access.ok is True
    assert access.role == "customer"
    assert frozenset(access.channels) == CUSTOMER_CHANNELS
    assert pair.channels == tuple(sorted(CUSTOMER_CHANNELS))
    assert authorize_control(access) == "founder_only"
    refresh_as_access = verify_access(pair.refresh, JWT, NOW)
    assert refresh_as_access.ok is False
    assert refresh_as_access.reason == "refresh_forbidden"
    assert authorize_control(refresh_as_access) == "refresh_forbidden"


def test_expired_and_empty_secret_deny() -> None:
    pair = issue_pair(JWT, role="customer", sub="c1", now=NOW)
    assert verify_access(pair.access, JWT, NOW + ACCESS_TTL_S + 1).reason == "expired"
    with pytest.raises(AuthClosed, match="jwt_secret_missing"):
        issue_pair("", role="customer", sub="c1", now=NOW)
    with pytest.raises(AuthClosed, match="jwt_secret_missing"):
        require_jwt_secret(environ={})
    assert load_jwt_secret(environ={}) == ""


def test_paper_customer_cap_is_five() -> None:
    assert PAPER_CUSTOMER_CAP == 5
    assert PAPER_IDENTITY_CAP == 6
    allow = paper_customer_allowlist(environ={"AAD_PAPER_CUSTOMERS": "c1,c2,c3,c4,c5"})
    assert allow == {"c1", "c2", "c3", "c4", "c5"}
    with pytest.raises(AuthClosed, match="paper_customer_cap"):
        paper_customer_allowlist(environ={"AAD_PAPER_CUSTOMERS": "c1,c2,c3,c4,c5,c6"})
    with pytest.raises(AuthClosed, match="unknown_customer"):
        login(
            role="customer",
            sub="c9",
            now=NOW,
            secret=JWT,
            environ={"AAD_PAPER_CUSTOMERS": "c1,c2,c3,c4,c5"},
        )


def test_login_and_refresh_session() -> None:
    pair = login(role="customer", sub="c1", now=NOW, secret=JWT, environ={})
    assert verify_access(pair.access, JWT, NOW).ok is True
    rotated = refresh_session(pair.refresh, now=NOW, secret=JWT)
    assert verify_access(rotated.access, JWT, NOW).ok is True
    assert verify_access(rotated.refresh, JWT, NOW).reason == "refresh_forbidden"
    founder = login(
        role="founder",
        sub="founder",
        now=NOW,
        secret=JWT,
        totp=totp_at(RFC_SEED, NOW),
        totp_secret=RFC_SEED,
        tfa=True,
    )
    decision = verify_access(founder.access, JWT, NOW)
    assert decision.tfa is True
    assert authorize_control(decision) is None


def test_cli_login_and_empty_secret(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("AAD_JWT_SECRET", JWT)
    assert auth_main(["login", "--role", "customer", "--sub", "c1", "--now", str(NOW)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["role"] == "customer"
    assert out["channels"] == ["signals:public"]
    assert out["orders"] == "REFUSED"
    monkeypatch.delenv("AAD_JWT_SECRET", raising=False)
    monkeypatch.delenv("AAD_JWT_SECRET_FILE", raising=False)
    monkeypatch.delenv("AAD_SECRETS_DIR", raising=False)
    monkeypatch.delenv("AAD_AGE_IDENTITY_FILE", raising=False)
    assert auth_main(["login", "--role", "customer", "--sub", "c1", "--now", str(NOW)]) == 2
    err = json.loads(capsys.readouterr().err)
    assert err["reason"] == "jwt_secret_missing"


def test_load_jwt_secret_from_file_and_store(tmp_path: Path) -> None:
    path = tmp_path / "jwt.txt"
    path.write_text(JWT + "\n", encoding="utf-8")
    assert load_jwt_secret(environ={"AAD_JWT_SECRET_FILE": str(path)}) == JWT
    from secretstore import generate_identity, open_store

    ident = generate_identity()
    store = open_store(secrets_dir=tmp_path, identity=ident)
    store.put_hmac_secret("jwt", JWT, ident.recipient())
    assert load_jwt_secret(environ={}, store=store) == JWT
    sealed = (tmp_path / "system" / "jwt.sops.json").read_text(encoding="utf-8")
    assert JWT not in sealed
