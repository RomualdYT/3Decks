#!/usr/bin/env bash
# Build the production C logic with host SDK boundary stubs; no console needed.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_build="$(mktemp -d "${TMPDIR:-/tmp}/3decks-tests.XXXXXX")"
trap 'rm -rf -- "$test_build"' EXIT
src="$repo/apps/console/source"
tests="$repo/apps/console/tests"
cc="${CC:-cc}"
flags=(-std=c11 -D_POSIX_C_SOURCE=200112L -Wall -Wextra -Werror -g -O1)
if [[ "${SANITIZE:-1}" == 1 ]]; then
    flags+=(-fsanitize=address,undefined,float-cast-overflow -fno-omit-frame-pointer)
fi
includes=(-I"$tests/stubs" -I"$tests")
for layer in app network protocol ui graphics platform; do includes+=(-I"$src/$layer"); done
common=("$tests/support.c" "$src/app/app_navigation.c" "$src/protocol/model.c")
protocol_sources=(
    "$src/protocol/json.c"
    "$src/protocol/protocol.c"
    "$src/protocol/extension_state.c"
    "$src/protocol/stream_chat.c"
    "$src/graphics/theme.c"
)
run() {
    local name="$1"; shift
    "$cc" "${flags[@]}" "${includes[@]}" "$tests/$name.c" "$@" -lm -o "$test_build/$name"
    "$test_build/$name"
}
run test_framing "$src/network/framing.c"
run test_decky "$src/graphics/decky.c"
"$cc" "${flags[@]}" -I"$src/graphics" "$repo/tools/export_decky_sprite.c" "$src/graphics/decky.c" -lm -o "$test_build/export-decky"
"$test_build/export-decky" "$test_build/decky.svg"
cmp "$test_build/decky.svg" "$repo/apps/desktop/frontend/public/decky.svg"
"$cc" "${flags[@]}" -I"$src/graphics" "$repo/tools/export_decky_brand.c" "$src/graphics/decky.c" -lm -o "$test_build/export-decky-brand"
"$test_build/export-decky-brand" "$test_build/logo.svg" logo
cmp "$test_build/logo.svg" "$repo/apps/desktop/frontend/public/decky-logo.svg"
"$test_build/export-decky-brand" "$test_build/banner.svg" en
cmp "$test_build/banner.svg" "$repo/docs/assets/3decks-banner.svg"
"$test_build/export-decky-brand" "$test_build/banner.fr.svg" fr
cmp "$test_build/banner.fr.svg" "$repo/docs/assets/3decks-banner.fr.svg"
run test_companion "$src/graphics/decky.c" "$src/ui/ui_companion.c" "$src/ui/ui_intro.c" "$src/graphics/theme.c" "$src/ui/i18n.c"
run test_localization "$src/ui/i18n.c"
run test_text_layout "$src/graphics/text_layout.c"
run test_text_cache "$src/graphics/text_cache.c"
run test_text_render "$src/graphics/text.c" "$src/graphics/text_layout.c" "$src/graphics/text_cache.c"
run test_render_pacing "$src/app/render_pacing.c"
run test_draw_geometry "$src/graphics/draw.c"
run test_interactions "${common[@]}" "$src/app/app_feedback.c" "$src/ui/ui_layout.c"
run test_protocol "${protocol_sources[@]}" "$src/protocol/model.c"
run test_network "${common[@]}" "$src/app/app_feedback.c" "$src/app/app_network.c" "$src/network/net.c" "$src/network/framing.c" "${protocol_sources[@]}"
