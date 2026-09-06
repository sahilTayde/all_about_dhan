"""Run: python -m api  (from apps/api with src on the path, or after pip install -e)."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
