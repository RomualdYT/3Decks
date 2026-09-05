#!/usr/bin/env bash
# Build the production C logic with host SDK boundary stubs; no console needed.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_build="$(mktemp -d "${TMPDIR:-/tmp}/3decks-tests.XXXXXX")"
trap 'rm -rf -- "$test_build"' EXIT
src="$repo/3ds-app/source"
tests="$repo/3ds-app/tests"
cc="${CC:-cc}"
flags=(-std=c11 -D_POSIX_C_SOURCE=200112L -Wall -Wextra -Werror -g -O1)
if [[ "${SANITIZE:-1}" == 1 ]]; then
    flags+=(-fsanitize=address,undefined,float-cast-overflow -fno-omit-frame-pointer)
fi
includes=(-I"$tests/stubs" -I"$tests")
for layer in app network protocol ui graphics platform; do includes+=(-I"$src/$layer"); done
common=("$tests/support.c" "$src/app/app_navigation.c" "$src/protocol/model.c")
run() {
    local name="$1"; shift
    "$cc" "${flags[@]}" "${includes[@]}" "$tests/$name.c" "$@" -lm -o "$test_build/$name"
    "$test_build/$name"
}
run test_framing "$src/network/framing.c"
run test_localization "$src/ui/i18n.c"
run test_text_layout "$src/graphics/text_layout.c"
run test_interactions "${common[@]}" "$src/app/app_feedback.c" "$src/ui/ui_layout.c"
run test_protocol "$src/protocol/json.c" "$src/protocol/protocol.c" "$src/protocol/model.c" "$src/protocol/extension_state.c" "$src/graphics/theme.c"
run test_network "${common[@]}" "$src/app/app_feedback.c" "$src/app/app_network.c" "$src/network/net.c" "$src/network/framing.c" "$src/protocol/json.c" "$src/protocol/protocol.c" "$src/protocol/extension_state.c" "$src/graphics/theme.c"
