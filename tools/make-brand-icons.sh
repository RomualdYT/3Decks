#!/usr/bin/env bash
# Rasterize at the displayed size: baked coverage, no runtime resampling.
set -euo pipefail
cd "$(dirname "$0")/.."
docker run --rm --entrypoint bash -v "$PWD:/repo" -w /repo \
  3decks-console-packaging:local -c '
    set -euo pipefail
    staging=$(mktemp -d)
    trap '\''rm -rf "$staging"'\'' EXIT
    rsvg-convert -w 16 -h 16 apps/console/packaging/brands/spotify.svg -o "$staging/spotify.png"
    tex3ds -f rgba8 -o "$staging/spotify.t3x" "$staging/spotify.png"
    mkdir -p apps/console/romfs/brands
    cp "$staging/spotify.t3x" apps/console/romfs/brands/spotify.t3x
  '
