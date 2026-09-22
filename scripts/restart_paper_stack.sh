#!/usr/bin/env bash
# Compatibility wrapper. Founder command is scripts/desk.sh
exec "$(cd "$(dirname "$0")" && pwd)/desk.sh" morning "$@"
