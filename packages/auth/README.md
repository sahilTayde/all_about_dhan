# auth (V2-23 + C5-02)

Fail-closed JWT and founder 2FA for the V2 gateway and founder control path.

**Paper only. No live orders. No secrets in git.** Signing keys and TOTP seeds live in env / files / secretstore (`AAD_JWT_SECRET`, `AAD_FOUNDER_TOTP_SECRET`). Empty key → deny. Query-string credentials are refused by the gateway.

C5-02 sizes the paper portal for **5 customers + founder**. Customer access claims are `signals:public` only. `aud` stays `aad-v2` (existing verify contract). Verify is in-process HMAC only — no secretstore I/O on the hot path.

| Piece | Behaviour |
|-------|-----------|
| Access JWT | HS256, 15 min, `aud=aad-v2`, `iss=aad-auth` |
| Refresh JWT | cannot subscribe or run founder commands |
| Founder 2FA | TOTP; missing seed or bad code → deny |
| Customer | `channels=["signals:public"]` only |
| Paper cap | 5 customer ids (`AAD_PAPER_CUSTOMERS`) + founder |
| Rates | REST 10/s, WS subscribe 5/s, commands 1/s (per identity) |

Stdlib HMAC JWT. `pyjwt` is still the later upgrade.

## Set `AAD_JWT_SECRET`

Never commit the value. Never paste it into chat.

### Paper localhost (Mac / 127.0.0.1)

Empty `AAD_JWT_SECRET` + bind `127.0.0.1` = localhost-dev (no JWT). To exercise C5-02 locally:

```bash
# gitignored .env — names only in .env.example
printf 'AAD_JWT_SECRET=%s\n' "$(openssl rand -hex 32)" >> .env
# optional founder 2FA seed (base32). Keep it out of git.
# AAD_FOUNDER_TOTP_SECRET=...
export AAD_PAPER_CUSTOMERS=c1,c2,c3,c4,c5
python -m auth login --role customer --sub c1
python -m auth login --role founder --sub founder --totp 123456
```

Or `AAD_JWT_SECRET_FILE=/path/outside/repo/jwt.hmac` (first line only).

### 5-customer paper host

Required before binding off loopback:

1. Put a long random HMAC in the host env or a file **outside git** (`AAD_JWT_SECRET` / `AAD_JWT_SECRET_FILE`).
2. Or seal it in secretstore as `system/jwt.sops.json` (`AAD_SECRETS_DIR` + `AAD_AGE_IDENTITY_FILE`). Login/issue read it once; verify uses the in-memory copy.
3. Set `AAD_PAPER_CUSTOMERS=c1,c2,c3,c4,c5` (max 5). A sixth id is refused.
4. Set `AAD_FOUNDER_TOTP_SECRET` so founder control stays 2FA.
5. Mint customer pairs with `python -m auth login --role customer --sub c1` (or `POST /v2/auth/login` on the allowlist). Hand the JWTs out of band.

`POST /v2/auth/refresh` rotates access. Refresh tokens cannot subscribe or command.

No live brokers. No marketing site.
