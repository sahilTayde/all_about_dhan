# auth (V2-23)

Fail-closed JWT and founder 2FA stubs for the V2 gateway and founder control path.

**Paper only. No live orders. No secrets in git.** Signing keys and TOTP seeds live in env / files (`AAD_JWT_SECRET`, `AAD_FOUNDER_TOTP_SECRET`). Empty key → deny. Query-string credentials are refused by the gateway.

| Piece | Behaviour |
|-------|-----------|
| Access JWT | HS256, 15 min, `aud=aad-v2`, `iss=aad-auth` |
| Refresh JWT | cannot subscribe or run founder commands |
| Founder 2FA | TOTP; missing seed or bad code → deny |
| Customer | `signals:public` only |
| Rates | REST 10/s, WS subscribe 5/s, commands 1/s |

Stdlib HMAC JWT. `pyjwt` waits for the V2-24 secret store.
