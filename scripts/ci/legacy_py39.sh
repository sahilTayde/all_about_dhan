#!/usr/bin/env bash
# Mac legacy desk guard: CPython 3.9 must import api.main and serve token-free paper routes.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="${PWD}/apps/api/src${PYTHONPATH:+:$PYTHONPATH}"
python -c 'import api.main'
python - <<'PY'
from fastapi.testclient import TestClient

from api.main import create_app

client = TestClient(create_app(), base_url="http://127.0.0.1:8000")
for path in ("/health", "/paper/founder-book"):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code, response.text)
print("legacy-py39 ok")
PY
