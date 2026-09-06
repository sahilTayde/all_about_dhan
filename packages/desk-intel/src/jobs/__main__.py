"""Scheduled desk jobs.

  python -m jobs pre-market --offline
  python -m jobs post-market --offline   # recon, then Docs Auditor
"""

from __future__ import annotations

import sys

from desk_intel.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
