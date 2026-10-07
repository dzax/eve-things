#!/usr/bin/env bash
# Copy the SDE jsonl files the app needs from a local SDE checkout into assets/sde, gzipped individually.
# Usage: scripts/pull_sde.sh [SDE_JSONL_DIR]   (default: ./sde/jsonl)
set -euo pipefail

FILES=(
    _sde.jsonl
    planetSchematics.jsonl
    types.jsonl
)

root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
src="${1:-$root/sde/jsonl}"
dest="$root/assets/sde"

[[ -d "$src" ]] || { echo "SDE jsonl directory not found: $src" >&2; exit 1; }

mkdir -p "$dest"
for file in "${FILES[@]}"; do
    [[ -f "$src/$file" ]] || { echo "Missing SDE file: $src/$file" >&2; exit 1; }
    # -n omits the name/timestamp so unchanged data produces identical archives.
    gzip -9 -n -c "$src/$file" >"$dest/$file.gz.tmp"
    mv "$dest/$file.gz.tmp" "$dest/$file.gz"
    echo "Wrote $dest/$file.gz"
done
