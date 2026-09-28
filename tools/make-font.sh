#!/usr/bin/env bash
#
# Génère la police embarquée de l'application.
#
# Pourquoi une police dédiée : la police système de la console est un bitmap
# dont la hauteur de glyphe est de trente pixels. L'afficher à petite taille
# revient à la réduire, ce qui détruit l'information et rend le texte
# illisible, sans qu'aucun filtrage puisse le rattraper.
#
# On génère donc une police matricielle à la taille réellement affichée. Les
# facteurs d'échelle restent alors proches de 1, et le rendu est net.
#
# Inter est aussi utilisée par l'interface web. Sa licence OFL autorise son
# intégration et sa redistribution dans l'application, tout en couvrant les
# accents nécessaires aux interfaces française et anglaise.
#
# Usage :
#   ./tools/make-font.sh [taille] [chemin/police.ttf]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="devkitpro/devkitarm:latest"

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
