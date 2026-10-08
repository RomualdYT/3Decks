#!/usr/bin/env bash
#
# Génère la police embarquée de l'application.
#
# La taille en points contrôle la rasterisation du BCFNT. Citro2D normalise
# ensuite toutes les polices à une cellule de 30 pixels : le code d'affichage
# ne doit donc pas appliquer une seconde correction fondée sur cette taille.
#
# Inter est aussi utilisée par l'interface web. Sa licence OFL autorise son
# intégration et sa redistribution dans l'application, tout en couvrant les
# accents nécessaires aux interfaces française et anglaise.
#
# Usage :
#   ./tools/make-font.sh                       # famille native de production
#   ./tools/make-font.sh taille [police.ttf]    # police de repli historique

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${FONT_BUILD_IMAGE:-devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5}"

# No arguments: regenerate the validated native-size family.
if [ "$#" -eq 0 ]; then
    docker run --rm -v "$ROOT":/repo -w /repo "$IMAGE" \
        python3 tools/build_console_fonts.py
    exit 0
fi

SIZE="${1:-17}"
SOURCE="${2:-$ROOT/tools/fonts/Inter-Regular.ttf}"
OUTPUT="$ROOT/apps/console/romfs/deck.bcfnt"
CHARSET="$ROOT/tools/font-charset.txt"

if [ ! -f "$SOURCE" ]; then
	echo "Police source introuvable : $SOURCE" >&2
	echo "Indiquez un fichier TrueType en second argument." >&2
	echo >&2
	echo "Si tools/fonts/Inter-Regular.ttf manque, telechargez Inter depuis" >&2
	echo "https://github.com/rsms/inter/releases et placez-la a cet endroit." >&2
	exit 1
fi

# Une police propriétaire produirait un fichier que le projet n'aurait pas le
# droit de redistribuer. L'avertissement vaut mieux qu'une infraction découverte
# après publication.
case "$(basename "$SOURCE")" in
Verdana* | Arial* | Tahoma* | Calibri* | Georgia* | Times* | Helvetica* | SFNS*)
	echo "Attention : '$(basename "$SOURCE")' est une police propriétaire." >&2
	echo "Le fichier produit ne pourra pas etre redistribue avec le projet." >&2
	echo "Utilisez-la pour un essai local uniquement." >&2
	echo >&2
	;;
esac

if [ ! -f "$CHARSET" ]; then
	echo "Jeu de caractères introuvable : $CHARSET" >&2
	exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker est requis, ou installez devkitPro et utilisez mkbcfnt." >&2
	exit 1
fi

PLATFORM_ARG=()
case "$(uname -m)" in
arm64 | aarch64) PLATFORM_ARG=(--platform linux/amd64) ;;
esac

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cp "$SOURCE" "$WORK/source.ttf"
cp "$CHARSET" "$WORK/charset.txt"

echo "Génération d'une police de ${SIZE} points depuis $(basename "$SOURCE")..."

# La liste blanche limite la police aux caractères réellement employés par
# l'interface : sans elle, les milliers de glyphes de la police source
# produiraient un fichier plusieurs fois plus volumineux.
docker run --rm "${PLATFORM_ARG[@]}" -v "$WORK":/w -w /w "$IMAGE" \
	bash -c "export PATH=\$DEVKITPRO/tools/bin:\$PATH && \
		mkbcfnt -s ${SIZE} -w charset.txt -o deck.bcfnt source.ttf" |
	tail -2

if [ ! -f "$WORK/deck.bcfnt" ]; then
	echo "La génération a échoué." >&2
	exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
cp "$WORK/deck.bcfnt" "$OUTPUT"

SIZE_KB=$(($(wc -c <"$OUTPUT") / 1024))
echo
echo "Écrit : apps/console/romfs/deck.bcfnt (${SIZE_KB} Ko)"
echo "Recompilez avec ./build.sh pour l'embarquer."
