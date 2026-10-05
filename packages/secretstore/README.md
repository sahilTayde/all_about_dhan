# secretstore (V2-24)

Encrypted per-account broker credentials. **Paper / shadow only.** This package never
opens a Dhan session, never places an order, and never writes a real token into git.

## Now

- In-process `aad-age/v1` envelopes (X25519 + ChaCha20-Poly1305, age primitives).
- Decrypt only when a named account needs a broker session.
- Missing key, wrong key, missing/invalid envelope → refuse (`SecretClosed`).
- `/etc/aad/aad.env` remains the documented founder fallback
  (`AAD_SECRETS_ALLOW_ENV_FALLBACK=1`). Off by default.
- Vault and 1Password Connect are Protocol adapters and fail closed.

## Ops (names only)

| Env | Meaning |
|-----|---------|
| `AAD_SECRETS_DIR` | Directory of `accounts/<id>.sops.json` blobs |
| `AAD_AGE_IDENTITY_FILE` | Age-test identity file (outside the repo) |
| `AAD_SECRETS_ALLOW_ENV_FALLBACK` | `1` to allow founder `/etc/aad/aad.env` |
| `AAD_ENV_FALLBACK` | Override fallback path (default `/etc/aad/aad.env`) |

Identity files use the fake-looking `AGE-TEST-KEY-1` prefix. Never commit them.
The public repo scan (`scripts/ci/scan_repo.py`) must stay clean.

Optional C5-02 JWT HMAC: `system/jwt.sops.json` via `put_hmac_secret` / `hmac_secret`.
Issue/login may read it. Token verify does not.

V2-22 / V2-23 may land in parallel. This package talks to them through
`AccountDirectory` / `AccountRef` Protocols only.
