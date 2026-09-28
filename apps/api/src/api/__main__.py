"""Run: python -m api  (from apps/api with src on the path, or after pip install -e).

Binds 127.0.0.1 by default. Refuses 0.0.0.0 unless AAD_GATEWAY_TOKEN is set.
"""

from __future__ import annotations

import os

import uvicorn

from api.gateway_auth import (
    BIND_ENV,
    DEFAULT_BIND,
    assert_bind_allowed,
    load_gateway_auth,
)


def main() -> None:
    auth = load_gateway_auth()
    host = os.environ.get(BIND_ENV, DEFAULT_BIND).strip() or DEFAULT_BIND
    assert_bind_allowed(host, auth.configured)
    port = int(os.environ.get("AAD_GATEWAY_PORT", "8000"))
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
