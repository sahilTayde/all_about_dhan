"""V2-24: fake keys only. Missing/wrong key refuse. Round-trip. No plaintext in tree."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from secretstore import (
    AccountStub,
    AgeIdentity,
    BrokerCredential,
    FileSecretStore,
    MemoryAccounts,
    OnePasswordConnectAdapter,
    SecretClosed,
    VaultAdapter,
    generate_identity,
    open_store,
    parse_identity,
)
from secretstore.crypto import aead_open, aead_seal, x25519

REPO = Path(__file__).resolve().parents[3]
PKG = REPO / "packages" / "secretstore"


def _accounts(*ids: str) -> MemoryAccounts:
    rows = [AccountStub(i, kind="founder" if i == "founder" else "customer") for i in ids]
    return MemoryAccounts(rows)


def _store(
    tmp_path: Path,
    identity: AgeIdentity | None,
    *ids: str,
    allow_env_fallback: bool = False,
    env_fallback_path: Path | None = None,
) -> FileSecretStore:
    fallback = env_fallback_path if env_fallback_path is not None else tmp_path / "missing.env"
    return open_store(
        secrets_dir=tmp_path,
        identity=identity,
        accounts=_accounts(*ids),
        allow_env_fallback=allow_env_fallback,
        env_fallback_path=fallback,
    )


def test_rfc7748_x25519() -> None:
    alice = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    bob = bytes.fromhex("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb")
    alice_pub = bytes.fromhex("8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a")
    bob_pub = bytes.fromhex("de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f")
    shared = bytes.fromhex("4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742")
    nine = (9).to_bytes(32, "little")
    assert x25519(alice, nine) == alice_pub
    assert x25519(bob, nine) == bob_pub
    assert x25519(alice, bob_pub) == shared
    assert x25519(bob, alice_pub) == shared


def test_rfc8439_chacha20_poly1305() -> None:
    key = bytes.fromhex("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f")
    nonce = bytes.fromhex("070000004041424344454647")
    aad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
    plain = (
        b"Ladies and Gentlemen of the class of '99: If I could offer you only one "
        b"tip for the future, sunscreen would be it."
    )
    expect = bytes.fromhex(
        "d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d6"
        "3dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b36"
        "92ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc"
        "3ff4def08e4b7a9de576d26586cec64b61161ae10b594f09e26a7e902ecbd0600691"
    )
    got = aead_seal(key, nonce, plain, aad)
    assert got == expect
    assert aead_open(key, nonce, got, aad) == plain


def test_roundtrip_fake_broker_dict(tmp_path: Path) -> None:
    ident = generate_identity()
    store = _store(tmp_path, ident, "acct-paper")
    fake = {
        "account_id": "acct-paper",
        "broker": "dhan",
        "client_id": "fake-client-id",
        "access_token": "fake-access-token-for-tests-only",
    }
    cred = BrokerCredential(**fake)
    path = store.put_broker_credentials(cred, ident.recipient())
    text = path.read_text(encoding="utf-8")
    assert "fake-access-token-for-tests-only" not in text
    assert "fake-client-id" not in text
    assert json.loads(text)["v"] == "aad-age/v1"
    out = store.credentials_for_session("acct-paper")
    assert out.client_id == fake["client_id"]
    assert out.access_token == fake["access_token"]
    assert "fake-access-token-for-tests-only" not in repr(out)


def test_missing_identity_refuses(tmp_path: Path) -> None:
    ident = generate_identity()
    writer = _store(tmp_path, ident, "acct-paper")
    writer.put_broker_credentials(
        BrokerCredential("acct-paper", "dhan", "fake-client-id", "fake-access-token-for-tests-only"),
        ident.recipient(),
    )
    reader = _store(tmp_path, None, "acct-paper")
    with pytest.raises(SecretClosed, match="missing_identity"):
        reader.credentials_for_session("acct-paper")


def test_wrong_identity_refuses(tmp_path: Path) -> None:
    good = generate_identity()
    bad = generate_identity()
    writer = _store(tmp_path, good, "acct-paper")
    writer.put_broker_credentials(
        BrokerCredential("acct-paper", "dhan", "fake-client-id", "fake-access-token-for-tests-only"),
        good.recipient(),
    )
    reader = _store(tmp_path, bad, "acct-paper")
    with pytest.raises(SecretClosed, match="wrong_identity"):
        reader.credentials_for_session("acct-paper")


def test_missing_envelope_refuses(tmp_path: Path) -> None:
    ident = generate_identity()
    store = _store(tmp_path, ident, "acct-paper")
    with pytest.raises(SecretClosed, match="missing_envelope"):
        store.credentials_for_session("acct-paper")


def test_unknown_account_refuses(tmp_path: Path) -> None:
    ident = generate_identity()
    store = _store(tmp_path, ident, "acct-a")
    with pytest.raises(SecretClosed, match="unknown_account"):
        store.credentials_for_session("acct-b")


def test_account_a_cannot_open_account_b(tmp_path: Path) -> None:
    ident = generate_identity()
    store = _store(tmp_path, ident, "acct-a", "acct-b")
    store.put_broker_credentials(
        BrokerCredential("acct-a", "dhan", "fake-client-a", "fake-access-token-for-tests-aaa"),
        ident.recipient(),
    )
    with pytest.raises(SecretClosed, match="missing_envelope"):
        store.credentials_for_session("acct-b")
    blob = (tmp_path / "accounts" / "acct-a.sops.json").read_bytes()
    (tmp_path / "accounts" / "acct-b.sops.json").write_bytes(blob)
    with pytest.raises(SecretClosed, match="invalid_envelope"):
        store.credentials_for_session("acct-b")


def test_env_fallback_founder_when_enabled(tmp_path: Path) -> None:
    env_path = tmp_path / "aad.env"
    token = "fake" + "TokenForUnitTestOnly99"
    env_path.write_text(f"{'DHAN_CLIENT_ID'}={'fake-founder-id'}\n{'DHAN_ACCESS_TOKEN'}={token}\n", encoding="utf-8")
    store = _store(
        tmp_path,
        generate_identity(),
        "founder",
        allow_env_fallback=True,
        env_fallback_path=env_path,
    )
    out = store.credentials_for_session("founder")
    assert out.client_id == "fake-founder-id"
    assert out.access_token == token


def test_env_fallback_disabled_refuses(tmp_path: Path) -> None:
    env_path = tmp_path / "aad.env"
    token_key = "DHAN_" + "ACCESS_TOKEN"
    env_path.write_text(f"DHAN_CLIENT_ID=x\n{token_key}={'y' * 16}\n", encoding="utf-8")
    store = _store(
        tmp_path,
        generate_identity(),
        "founder",
        allow_env_fallback=False,
        env_fallback_path=env_path,
    )
    with pytest.raises(SecretClosed, match="missing_envelope"):
        store.credentials_for_session("founder")


def test_env_fallback_invalid_refuses(tmp_path: Path) -> None:
    env_path = tmp_path / "aad.env"
    env_path.write_text("# empty names only\nDHAN_CLIENT_ID=\nDHAN_ACCESS_TOKEN=\n", encoding="utf-8")
    store = _store(
        tmp_path,
        generate_identity(),
        "founder",
        allow_env_fallback=True,
        env_fallback_path=env_path,
    )
    with pytest.raises(SecretClosed, match="fallback_invalid"):
        store.credentials_for_session("founder")


def test_vault_and_onepassword_stubs_refuse() -> None:
    with pytest.raises(SecretClosed, match="adapter_not_configured"):
        VaultAdapter().get("acct-paper")
    with pytest.raises(SecretClosed, match="adapter_not_configured"):
        OnePasswordConnectAdapter().get("acct-paper")


def test_parse_identity_missing() -> None:
    with pytest.raises(SecretClosed, match="missing_identity"):
        parse_identity("")
    with pytest.raises(SecretClosed, match="missing_identity"):
        parse_identity("# comment only\n")


def test_package_has_no_dhan_or_live_imports() -> None:
    forbidden = ("import dhan_client", "from dhan_client", "DhanBroker", "place_order", "limited_live")
    for path in (PKG / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path}: {token}"


def test_repo_scan_has_no_plaintext_secret() -> None:
    begin = "-----" + "BEGIN"
    age_live = "AGE-" + "SECRET-KEY-1"
    for path in (PKG / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert begin not in text
        assert age_live not in text
    # Fake identities are generated at runtime; no hex identity is committed.
    tree = "\n".join(p.read_text(encoding="utf-8") for p in (PKG / "src").rglob("*.py"))
    assert "AGE-TEST-KEY-1" + ("a" * 64) not in tree
