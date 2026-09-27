#!/bin/sh
# Point this checkout at scripts/mac/hooks. Does not affect CI or other clones.
set -eu

root=$(git rev-parse --show-toplevel)
cd "$root"
git config core.hooksPath scripts/mac/hooks
printf '%s\n' \
  "Installed Mac operations hooks (core.hooksPath=scripts/mac/hooks)." \
  "Undo: git config --unset core.hooksPath"
