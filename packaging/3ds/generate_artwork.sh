#!/usr/bin/env bash
# Run with a host C compiler, librsvg and the bundled Inter font installed.
set -euo pipefail
case "${1:-write}" in write|--check) ;; *) echo "Usage: $0 [--check]" >&2; exit 1;; esac
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
artwork_build="$(mktemp -d)"
trap 'rm -rf -- "$artwork_build"' EXIT
cc -std=c11 -Wall -Wextra -Werror -I"$repo/3ds-app/source/graphics" \
  "$repo/tools/export_home_menu.c" "$repo/3ds-app/source/graphics/decky.c" \
  -lm -o "$artwork_build/export"
for variant in icon banner; do
  "$artwork_build/export" "$artwork_build/$variant.svg" "$variant"
  rsvg-convert "$artwork_build/$variant.svg" -o "$artwork_build/$variant.png"
  if [[ "${1:-write}" == --check ]]; then
    cmp "$artwork_build/$variant.png" "$repo/packaging/3ds/$variant.png"
  else
    cp "$artwork_build/$variant.png" "$repo/packaging/3ds/$variant.png"
  fi
done
