#!/bin/sh
# Point this checkout at scripts/mac/hooks. Does not affect CI or other clones.
# Hooks read scripts/mac/protected_paths.txt (V2 paths only).
set -eu

root=$(git rev-parse --show-toplevel)
cd "$root"
git config core.hooksPath scripts/mac/hooks
printf '%s\n' \
  "Installed Mac V2-guard hooks (core.hooksPath=scripts/mac/hooks)." \
  "Protected paths: scripts/mac/protected_paths.txt" \
  "Undo: git config --unset core.hooksPath"
