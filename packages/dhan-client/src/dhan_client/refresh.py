"""Token refresh notes. VERIFY FROM DOCS — nothing here calls Dhan.

Official page: https://dhanhq.co/docs/v2/authentication/

What the docs *do* show
-----------------------
- Individual access tokens from Dhan Web last **24 hours**.
- ``RenewToken``: ``https://api.dhan.co/v2/RenewToken``
  Headers in the official curl: ``access-token``, ``dhanClientId``.
  Note: most other REST pages use header ``client-id``, not ``dhanClientId``.
- Docs: "This API expires your current token and provides you with a new token
  with another 24 hours of validity. You can use this only for tokens generated
  from Dhan Web."
- Docs: expired tokens cannot be renewed.
- TOTP generate: ``POST https://auth.dhan.co/app/generateAccessToken`` with
  query ``dhanClientId``, ``pin``, ``totp`` — **not implemented** (PIN/TOTP
  must never be logged or committed).
- Individual OAuth: ``app_id`` / ``app_secret`` headers (12-month key/secret),
  three-step consent flow. **not implemented**.

UNKNOWN / VERIFY
----------------
- HTTP method for RenewToken: official curl has no ``-X``. Do not assume POST.
- Response JSON field name for the new token: the RenewToken section does not
  include a response body on the docs page we fetched.
- Env ``DHAN_REFRESH_TOKEN``: **not** a field on the official RenewToken curl.
  Do not treat it as an OAuth refresh_token unless Dhan documents that.
- Env ``DHAN_CLIENT_SECRET``: official individual flow uses ``app_secret``,
  partner flow uses ``partner_secret``. Mapping is VERIFY FROM DOCS.
"""

from __future__ import annotations

from dhan_client.errors import NotImplementedInSkeleton


def renew_access_token(*_args: object, **_kwargs: object) -> None:
    raise NotImplementedInSkeleton(
        "Token refresh is not implemented in this skeleton. "
        "Read https://dhanhq.co/docs/v2/authentication/ (RenewToken) before wiring. "
        "Calling it incorrectly can invalidate a still-valid access token."
    )
