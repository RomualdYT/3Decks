"""Extraction de la couleur dominante d'une pochette.

Cette couleur sert d'accent à l'interface de la console : le fond du mode
« cadre à musique » et les liserés s'accordent alors au morceau écouté.

L'analyse est faite sur la texture déjà convertie, ce qui évite de redécoder
l'image. Deux écueils sont traités :

- une moyenne arithmétique donne toujours un gris terne, car les couleurs
  opposées s'annulent ; on regroupe donc les pixels par teinte et on retient la
  classe la plus fournie ;
- la teinte retenue est souvent trop sombre pour servir d'accent lisible sur un
  fond noir ; on la ravive donc jusqu'à une luminosité minimale.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

#: Pas d'échantillonnage. Un pixel sur quatre suffit et divise le coût d'autant.
_STEP = 4

#: Seuils écartant ce qui ne peut pas servir d'accent.
_MIN_LEVEL = 40  # trop sombre
_MAX_LEVEL = 235  # presque blanc
_MIN_SATURATION = 0.18  # gris

#: Luminosité visée pour l'accent final, sur 255.
_TARGET_LEVEL = 190


def dominant(texture: bytes) -> tuple[int, int, int] | None:
    """Couleur dominante d'une texture RGB565, ou `None` si indéterminable."""
    if not texture or len(texture) < 2:
        return None

    # Regroupement par classes de teinte grossières : les pixels d'une même
    # famille chromatique se cumulent, ce qui fait émerger la couleur réellement
    # présente plutôt qu'une moyenne sans caractère.
    buckets: dict[tuple[int, int, int], list[int]] = {}

    for offset in range(0, len(texture) - 1, 2 * _STEP):
        value = texture[offset] | (texture[offset + 1] << 8)

        red = ((value >> 11) & 0x1F) << 3
        green = ((value >> 5) & 0x3F) << 2
        blue = (value & 0x1F) << 3

        highest = max(red, green, blue)
        if highest < _MIN_LEVEL or highest > _MAX_LEVEL:
            continue

        lowest = min(red, green, blue)
        if (highest - lowest) / highest < _MIN_SATURATION:
            continue

        key = (red >> 5, green >> 5, blue >> 5)
        entry = buckets.setdefault(key, [0, 0, 0, 0])
        entry[0] += red
        entry[1] += green
        entry[2] += blue
        entry[3] += 1

    if not buckets:
        return None

    best = max(buckets.values(), key=lambda entry: entry[3])
    count = best[3]

    return _brighten(best[0] // count, best[1] // count, best[2] // count)


def _brighten(red: int, green: int, blue: int) -> tuple[int, int, int]:
    """Ravive une couleur trop sombre en conservant sa teinte.

    Les composantes sont multipliées par un même facteur : le rapport entre
    elles est préservé, donc la teinte ne dérive pas.
    """
    highest = max(red, green, blue)
    if highest <= 0:
        return (128, 128, 128)

    if highest < _TARGET_LEVEL:
        factor = _TARGET_LEVEL / highest
        red = min(255, int(red * factor))
        green = min(255, int(green * factor))
        blue = min(255, int(blue * factor))

    return (red, green, blue)


def to_hex(color: tuple[int, int, int]) -> str:
    return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
