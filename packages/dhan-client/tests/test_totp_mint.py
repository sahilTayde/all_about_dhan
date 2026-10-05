"""C5-06 TOTP mint: mocked HTTP only. Never call auth.dhan.co."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from dhan_client.config import ENV_ACCESS_TOKEN, ENV_CLIENT_ID, ENV_PIN, ENV_TOTP_SECRET
from dhan_client.endpoints import AUTH_BASE, GENERATE_ACCESS_TOKEN
from dhan_client.errors import MintError
from dhan_client.totp_mint import (
    GENERATE_URL,
    check_mint,
    http_post_generate,
    run_mint,
    totp_at,
    totp_secret_valid,
    upsert_env_key,
)
from dhan_client.__main__ import main

# RFC 6238 Appendix B seed (ASCII 12345678901234567890) as base32. Test vector only.
RFC_SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
FAKE_TOKEN = "test-access-token"
FAKE_PIN = "1357"
FAKE_CLIENT = "1100000001"


def _vault_env() -> dict[str, str]:
    return {
        ENV_CLIENT_ID: FAKE_CLIENT,
        ENV_PIN: FAKE_PIN,
        ENV_TOTP_SECRET: RFC_SEED,
    }


def _ok_http(url: str, params: dict[str, str]) -> dict[str, str]:
    assert url == GENERATE_URL
    assert url == f"{AUTH_BASE}{GENERATE_ACCESS_TOKEN}"
    assert "?" not in url
    assert params["dhanClientId"] == FAKE_CLIENT
    assert params["pin"] == FAKE_PIN
    assert params["totp"] == totp_at(RFC_SEED, 59)
    return {"accessToken": FAKE_TOKEN, "expiryTime": "2099-01-01 00:00:00"}


def test_official_generate_url() -> None:
    assert GENERATE_URL == "https://auth.dhan.co/app/generateAccessToken"
    assert GENERATE_ACCESS_TOKEN == "/app/generateAccessToken"


def test_rfc6238_totp_vector() -> None:
    assert totp_at(RFC_SEED, 59) == "287082"
    assert totp_secret_valid(RFC_SEED) is True
    assert totp_secret_valid("") is False
    assert totp_secret_valid("@@@") is False
    with pytest.raises(MintError, match="totp_secret_invalid"):
        totp_at("", 59)


def test_check_ready_without_http() -> None:
    report = check_mint(environ=_vault_env(), load_file=False, keychain=lambda _s: "")
    assert report.ready is True
    assert report.client_id_set is True
    assert report.pin_set is True
    assert report.totp_secret_set is True
    assert report.totp_secret_valid is True
    assert report.token_key == ENV_ACCESS_TOKEN
    assert report.env_path.endswith(".env")
    assert "http_post" not in check_mint.__code__.co_varnames


def test_check_reports_missing_names(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(f"{ENV_CLIENT_ID}={FAKE_CLIENT}\n", encoding="utf-8")
    report = check_mint(
        environ={},
        env_path=env_path,
        load_file=True,
        keychain=lambda _s: "",
    )
    assert report.ready is False
    assert report.client_id_set is True
    assert report.pin_set is False
    assert ENV_PIN in report.missing_names
    assert ENV_TOTP_SECRET in report.missing_names


def test_check_keychain_fallback() -> None:
    store = {
        ENV_CLIENT_ID: FAKE_CLIENT,
        ENV_PIN: FAKE_PIN,
        ENV_TOTP_SECRET: RFC_SEED,
    }
    report = check_mint(
        environ={},
        load_file=False,
        keychain=lambda name: store.get(name, ""),
    )
    assert report.ready is True
    assert report.pin_set is True


def test_refuses_overwrite_without_vault(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(f"{ENV_ACCESS_TOKEN}=keep-old\n", encoding="utf-8")
    called = {"n": 0}

    def boom(url: str, params: dict[str, str]) -> dict[str, str]:
        called["n"] += 1
        return {"accessToken": "nope"}

    with pytest.raises(MintError, match="vault_material_missing"):
        run_mint(
            environ={ENV_CLIENT_ID: FAKE_CLIENT},
            env_path=env_path,
            load_file=False,
            keychain=lambda _s: "",
            http_post=boom,
        )
    assert called["n"] == 0
    assert env_path.read_text(encoding="utf-8") == f"{ENV_ACCESS_TOKEN}=keep-old\n"


def test_mint_writes_env_and_redacts_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        f"{ENV_CLIENT_ID}={FAKE_CLIENT}\n{ENV_ACCESS_TOKEN}=old-token\n",
        encoding="utf-8",
    )
    caplog.set_level(logging.INFO)
    result = run_mint(
        environ=_vault_env(),
        env_path=env_path,
        load_file=False,
        keychain=lambda _s: "",
        now=59,
        http_post=_ok_http,
    )
    assert result.wrote is True
    assert result.token_set is True
    assert result.expiry_time == "2099-01-01 00:00:00"
    assert result.token_key == ENV_ACCESS_TOKEN
    text = env_path.read_text(encoding="utf-8")
    assert f"{ENV_ACCESS_TOKEN}={FAKE_TOKEN}" in text
    assert f"{ENV_CLIENT_ID}={FAKE_CLIENT}" in text
    blob = " ".join(rec.getMessage() for rec in caplog.records)
    assert FAKE_PIN not in blob
    assert RFC_SEED not in blob
    assert FAKE_TOKEN not in blob
    assert "1357" not in blob
    assert "generateAccessToken?dhanClientId" not in blob
    assert "pin=" not in blob
    assert "totp=" not in blob
    assert "query not logged" in blob


def test_mint_rejects_jwtish_expiry_echo(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"

    def http(url: str, params: dict[str, str]) -> dict[str, str]:
        return {"accessToken": FAKE_TOKEN, "expiryTime": "eyJhbGciOiJIUzI1NiIsInR5cCI6"}

    result = run_mint(
        environ=_vault_env(),
        env_path=env_path,
        load_file=False,
        keychain=lambda _s: "",
        now=59,
        http_post=http,
    )
    assert result.expiry_time == "REDACTED"


def test_http_post_refuses_query_in_url() -> None:
    with pytest.raises(MintError, match="request_url_must_not_include_query"):
        http_post_generate(
            GENERATE_URL + "?dhanClientId=x&pin=1&totp=2",
            {},
        )


def test_upsert_creates_0600(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    upsert_env_key(path, ENV_ACCESS_TOKEN, FAKE_TOKEN)
    assert path.read_text(encoding="utf-8") == f"{ENV_ACCESS_TOKEN}={FAKE_TOKEN}\n"
    assert (path.stat().st_mode & 0o777) == 0o600


def test_cli_check_no_network(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "dhan_client.totp_mint.check_mint",
        lambda: check_mint(environ=_vault_env(), load_file=False, keychain=lambda _s: ""),
    )
    rc = main(["mint-token", "--check"])
    out = capsys.readouterr().out
    assert rc == 0
    assert '"ready": true' in out
    assert '"network": false' in out
    assert FAKE_PIN not in out
    assert RFC_SEED not in out
    assert FAKE_TOKEN not in out


def test_cli_dry_run_is_check(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {"check": None}

    def fake_cmd(*, check: bool) -> int:
        seen["check"] = check
        return 0

    monkeypatch.setattr("dhan_client.__main__.cmd_mint_token", fake_cmd)
    assert main(["--dry-run", "mint-token"]) == 0
    assert seen["check"] is True


def test_cli_mint_failure_is_code_only(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def boom(**_kwargs: object) -> None:
        raise MintError("vault_material_missing:DHAN_PIN")

    monkeypatch.setattr("dhan_client.totp_mint.run_mint", boom)
    rc = main(["mint-token"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "vault_material_missing" in out
    assert FAKE_PIN not in out
