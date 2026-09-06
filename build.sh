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
#   ./build.sh cia      build installable HOME-menu package and 3DSX
#   ./build.sh all      build CIA and 3DSX

set -euo pipefail

IMAGE="devkitpro/devkitarm:latest"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT/3ds-app"
APP_VERSION="${APP_VERSION:-1}"
if [[ ! "$APP_VERSION" =~ ^[0-9]{1,5}$ ]] || (( 10#$APP_VERSION > 65535 )); then
	echo "APP_VERSION must be an integer from 0 to 65535." >&2
	exit 1
fi
APP_VERSION=$((10#$APP_VERSION))

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker est requis pour compiler l'application 3DS." >&2
	echo "Autre possibilite : installer devkitPro et lancer 'make' dans 3ds-app/." >&2
	exit 1
fi

# The official image supports native Docker platforms, including Apple Silicon.

case "${1:-build}" in
cia | all)
	IMAGE="3decks-console-packaging:local"
	docker build -t "$IMAGE" -f "$ROOT/packaging/3ds/Dockerfile" "$ROOT"
	;;
esac

run_make() {
	DOCKER_APP_DIR="$ROOT"
	CONVERSION_EXCLUSION=
	case "${OSTYPE:-}" in
	msys* | cygwin*)
		DOCKER_APP_DIR="$(cygpath -w "$ROOT")"
		CONVERSION_EXCLUSION='*'
		;;
	esac
	MSYS2_ARG_CONV_EXCL="$CONVERSION_EXCLUSION" docker run --rm \
		-e APP_VERSION="$APP_VERSION" \
		-v "$DOCKER_APP_DIR":/repo -w /repo/3ds-app \
		"$IMAGE" \
		bash -c 'export PATH=$DEVKITARM/bin:$DEVKITPRO/tools/bin:$PATH && make '"$1"' 2>&1' |
		sed -E '/modification time|Clock skew/d'
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
cia)
	run_make "$1"
	;;
all)
	run_make release
	;;
*)
	echo "Usage : $0 [build|clean|rebuild|cia|all]" >&2
	exit 1
	;;
esac

case "${1:-build}" in
cia | all)
	echo "Built: 3ds-app/deck3ds.cia"
	echo "CIA: install with FBI on a CFW-enabled console, then open 3Decks from HOME."
	;;
esac

if [ -f "$APP_DIR/deck3ds.3dsx" ]; then
	SIZE=$(du -h "$APP_DIR/deck3ds.3dsx" | cut -f1)
	echo
	echo "Construit : 3ds-app/deck3ds.3dsx ($SIZE)"
	echo
	echo "Installation sur la console :"
	echo "  1. copier deck3ds.3dsx dans sdmc:/3ds/"
	echo "  2. demarrer l'agent sur l'ordinateur"
	echo "  3. choisir l'ordinateur detecte automatiquement sur la console"
	echo "     (adresse et port restent disponibles dans Configuration manuelle)"
fi
