"""Catalogue des services optionnels proposés dans les réglages."""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    capability: str | None
    title_fr: str
    title_en: str
    description_fr: str
    description_en: str
    parent: str | None = None
    platforms: tuple[str, ...] = ("darwin", "win32")

    def as_payload(self) -> dict[str, object]:
        return {
            "key": self.key,
            "capability": self.capability,
            "title": {"fr": self.title_fr, "en": self.title_en},
            "description": {
                "fr": self.description_fr,
                "en": self.description_en,
            },
            "parent": self.parent,
            "platforms": list(self.platforms),
        }


FEATURE_SPECS = {
    spec.key: spec
    for spec in (
        FeatureSpec(
            "notifications",
            "notifications",
            "Notifications",
            "Notifications",
            "Affiche les notifications récentes du système sur la console.",
            "Shows recent system notifications on the console.",
        ),
        FeatureSpec(
            "media",
            "media",
            "Lecture multimédia",
            "Media playback",
            "Affiche le morceau, l’artiste et la progression de lecture.",
            "Shows the current track, artist and playback progress.",
        ),
        FeatureSpec(
            "media_artwork",
            "media_artwork",
            "Pochette d’album",
            "Album artwork",
            "Transmet la pochette et sa couleur dominante à la console.",
            "Sends album artwork and its dominant colour to the console.",
            parent="media",
        ),
        FeatureSpec(
            "windows",
            "windows",
            "Fenêtres et applications",
            "Windows and applications",
            "Affiche l’application active et alimente les pages de fenêtres.",
            "Shows the active app and powers dynamic window pages.",
        ),
        FeatureSpec(
            "audio_output",
            "audio_output",
            "Sorties audio",
            "Audio outputs",
            "Affiche et permet de changer le périphérique audio actif.",
            "Shows and lets you change the active audio device.",
        ),
        FeatureSpec(
            "system_stats",
            "system_stats",
            "Statistiques système",
            "System statistics",
            "Affiche l’utilisation du processeur et de la mémoire.",
            "Shows processor and memory usage.",
        ),
        FeatureSpec(
            "apple_music",
            None,
            "Apple Music",
            "Apple Music",
            "Autorise la lecture et le contrôle d’Apple Music.",
            "Allows reading and controlling Apple Music.",
            parent="media",
            platforms=("darwin",),
        ),
        FeatureSpec(
            "spotify",
            None,
            "Spotify",
            "Spotify",
            "Autorise la lecture et le contrôle de Spotify.",
            "Allows reading and controlling Spotify.",
            parent="media",
            platforms=("darwin",),
        ),
    )
}
