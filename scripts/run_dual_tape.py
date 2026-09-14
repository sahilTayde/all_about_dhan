#!/usr/bin/env python3
"""Founder dual-tape wrapper. No orders. No LLM."""

from __future__ import annotations

import sys

from trading_agents_india.__main__ import main

if __name__ == "__main__":
    argv = ["dual-tape", *sys.argv[1:]]
    raise SystemExit(main(argv))
