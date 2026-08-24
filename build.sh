#!/usr/bin/env bash
#
# Compile l'application 3DS dans un conteneur devkitPro.
#
# Aucune installation locale de devkitPro n'est requise : seul Docker est
# necessaire. Le resultat est 3ds-app/deck3ds.3dsx.
#
# Usage :
#   ./build.sh          compile
#   ./build.sh clean    nettoie
#   ./build.sh rebuild  nettoie puis compile

set -euo pipefail

IMAGE="devkitpro/devkitarm:latest"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT/3ds-app"

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker est requis pour compiler l'application 3DS." >&2
	echo "Autre possibilite : installer devkitPro et lancer 'make' dans 3ds-app/." >&2
	exit 1
fi

# L'image officielle est construite pour amd64. Sur une machine Apple Silicon,
# Docker l'execute par emulation : la compilation est un peu plus lente mais le
# resultat est identique.
PLATFORM_ARG=()
case "$(uname -m)" in
arm64 | aarch64)
	PLATFORM_ARG=(--platform linux/amd64)
	;;
esac

run_make() {
	DOCKER_APP_DIR="$APP_DIR"
	CONVERSION_EXCLUSION=
	case "${OSTYPE:-}" in
	msys* | cygwin*)
		DOCKER_APP_DIR="$(cygpath -w "$APP_DIR")"
		CONVERSION_EXCLUSION='*'
		;;
	esac
	MSYS2_ARG_CONV_EXCL="$CONVERSION_EXCLUSION" docker run --rm "${PLATFORM_ARG[@]}" \
		-v "$DOCKER_APP_DIR":/work -w /work \
		"$IMAGE" \
		bash -c 'export PATH=$DEVKITARM/bin:$DEVKITPRO/tools/bin:$PATH && make '"$1"' 2>&1' |
		grep -vE "modification time|Clock skew" || true
}

case "${1:-build}" in
clean)
	echo "Nettoyage..."
	run_make clean
	echo "Termine."
	;;
rebuild)
	run_make clean
	run_make ""
	;;
build | "")
	echo "Compilation de l'application 3DS..."
	run_make ""
	;;
*)
	echo "Usage : $0 [build|clean|rebuild]" >&2
	exit 1
	;;
esac

if [ -f "$APP_DIR/deck3ds.3dsx" ]; then
	SIZE=$(du -h "$APP_DIR/deck3ds.3dsx" | cut -f1)
	echo
	echo "Construit : 3ds-app/deck3ds.3dsx ($SIZE)"
	echo
	echo "Installation sur la console :"
	echo "  1. copier deck3ds.3dsx dans sdmc:/3ds/"
	echo "  2. copier 3ds-app/settings.cfg dans sdmc:/3ds/deck3ds/"
	echo "  3. y renseigner l'adresse affichee par l'agent"
fi
