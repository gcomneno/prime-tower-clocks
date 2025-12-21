#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash tools/run_monsters.sh
#
# Assumes you're in the repo root and monsters.txt exists.

OUTDIR="out"
mkdir -p "$OUTDIR"

while IFS= read -r N; do
  N="$(echo "$N" | tr -d ' \t\r')"
  [[ -z "$N" ]] && continue
  [[ "$N" =~ ^# ]] && continue

  echo
  echo ">>> N=$N"
  python3 prime_tower_clocks.py "$N" --dump-jsonl "$OUTDIR/$N.jsonl" --reconstruct
done < monsters.txt
