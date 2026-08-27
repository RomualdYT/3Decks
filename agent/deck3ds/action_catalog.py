"""Catalogue unique des actions proposées par Deck3DS.

Le validateur, l'API et l'éditeur consomment les mêmes descriptions. Ajouter
une action ne doit ainsi plus demander de synchroniser plusieurs tables Python
et une table JavaScript distincte.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionArgument:
    """Champ configurable d'une action."""

    name: str
    field_type: str = "text"
    required: bool = True

    def as_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.field_type,
            "required": self.required,
        }


@dataclass(frozen=True)
class ActionSpec:
    """Contrat d'exécution et présentation d'une action."""

    category: str
    icon: str
    color: str
    title_fr: str
    title_en: str
    description_fr: str
    description_en: str
    capability: str | None = None
    arguments: tuple[ActionArgument, ...] = ()

    def presentation_payload(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "icon": self.icon,
            "color": self.color,
            "title": {"fr": self.title_fr, "en": self.title_en},
            "description": {
                "fr": self.description_fr,
                "en": self.description_en,
            },
        }


def _arg(name: str, field_type: str = "text") -> ActionArgument:
    return ActionArgument(name, field_type)


def _action(
    category: str,
    icon: str,
    color: str,
    title_fr: str,
    title_en: str,
    description_fr: str,
    description_en: str,
    *,
    capability: str | None = None,
    arguments: tuple[ActionArgument, ...] = (),
) -> ActionSpec:
    return ActionSpec(
        category,
        icon,
        color,
        title_fr,
        title_en,
        description_fr,
        description_en,
        capability,
        arguments,
    )


ACTION_SPECS = {
    "app.launch": _action(
        "essential",
        "app",
        "#4F8DF7",
        "Ouvrir une application",
        "Open an application",
        "Lance ou remet au premier plan un programme.",
        "Launches or focuses a program.",
        capability="apps",
        arguments=(_arg("target"),),
    ),
    "hotkey": _action(
        "essential",
        "star",
        "#7C6BF2",
        "Raccourci clavier",
        "Keyboard shortcut",
        "Déclenche une combinaison de touches.",
        "Runs a keyboard shortcut.",
        capability="hotkey",
        arguments=(_arg("keys", "hotkey"),),
    ),
    "url.open": _action(
        "essential",
        "browser",
        "#36A6D8",
        "Ouvrir un site web",
        "Open a website",
        "Ouvre une adresse dans le navigateur.",
        "Opens an address in the browser.",
        capability="open_url",
        arguments=(_arg("url"),),
    ),
    "path.open": _action(
        "essential",
        "folder",
        "#D99B46",
        "Ouvrir un fichier ou dossier",
        "Open a file or folder",
        "Ouvre un élément dans l’explorateur de fichiers.",
        "Opens an item in the file explorer.",
        capability="open_path",
        arguments=(_arg("path"),),
    ),
    "volume.up": _action(
        "audio",
        "volume-up",
        "#3B82F6",
        "Monter le volume",
        "Volume up",
        "Augmente le volume de l’ordinateur.",
        "Raises the computer volume.",
        capability="volume",
    ),
    "volume.down": _action(
        "audio",
        "volume-down",
        "#3B82F6",
        "Baisser le volume",
        "Volume down",
        "Baisse le volume de l’ordinateur.",
        "Lowers the computer volume.",
        capability="volume",
    ),
    "volume.set": _action(
        "audio",
        "volume-up",
        "#3B82F6",
        "Régler le volume",
        "Set volume",
        "Applique un niveau précis.",
        "Sets a precise volume level.",
        capability="volume",
        arguments=(_arg("value", "number"),),
    ),
    "volume.mute_toggle": _action(
        "audio",
        "volume-mute",
        "#F59E0B",
        "Couper / rétablir le son",
        "Mute / unmute",
        "Bascule le son général.",
        "Toggles system sound.",
        capability="mute",
    ),
    "mic.mute_toggle": _action(
        "audio",
        "mic",
        "#F59E0B",
        "Couper / activer le micro",
        "Mute / unmute mic",
        "Bascule le microphone système.",
        "Toggles the system microphone.",
        capability="mic",
    ),
    "mic.mute": _action(
        "audio",
        "mic-off",
        "#EF6A71",
        "Couper le micro",
        "Mute microphone",
        "Force le microphone en sourdine.",
        "Forces the microphone off.",
        capability="mic",
    ),
    "mic.unmute": _action(
        "audio",
        "mic",
        "#45C995",
        "Activer le micro",
        "Unmute microphone",
        "Force le microphone actif.",
        "Forces the microphone on.",
        capability="mic",
    ),
    "audio_output.cycle": _action(
        "audio",
        "volume-up",
        "#8B78EA",
        "Changer de sortie audio",
        "Cycle audio output",
        "Passe au casque, aux enceintes ou à l’écran suivant.",
        "Cycles headphones, speakers and displays.",
        capability="audio_output",
    ),
    "audio_output.set": _action(
        "audio",
        "volume-up",
        "#8B78EA",
        "Choisir une sortie audio",
        "Choose audio output",
        "Sélectionne une sortie par son nom.",
        "Selects an output by name.",
        capability="audio_output",
        arguments=(_arg("target"),),
    ),
    "app_volume.up": _action(
        "audio",
        "music",
        "#8B78EA",
        "Monter le volume du lecteur",
        "Player volume up",
        "Ajuste uniquement le lecteur musical.",
        "Adjusts only the music player.",
        capability="app_volume",
    ),
    "app_volume.down": _action(
        "audio",
        "music",
        "#8B78EA",
        "Baisser le volume du lecteur",
        "Player volume down",
        "Ajuste uniquement le lecteur musical.",
        "Adjusts only the music player.",
        capability="app_volume",
    ),
    "app_volume.set": _action(
        "audio",
        "music",
        "#8B78EA",
        "Régler le volume du lecteur",
        "Set player volume",
        "Applique un niveau précis au lecteur.",
        "Sets a precise player volume.",
        capability="app_volume",
        arguments=(_arg("value", "number"),),
    ),
    "media.play_pause": _action(
        "media",
        "play",
        "#5C8DFF",
        "Lecture / pause",
        "Play / pause",
        "Pilote la lecture en cours.",
        "Controls current playback.",
        capability="media",
    ),
    "media.next": _action(
        "media",
        "next",
        "#5C8DFF",
        "Piste suivante",
        "Next track",
        "Passe au média suivant.",
        "Skips to the next item.",
        capability="media",
    ),
    "media.previous": _action(
        "media",
        "previous",
        "#5C8DFF",
        "Piste précédente",
        "Previous track",
        "Revient au média précédent.",
        "Returns to the previous item.",
        capability="media",
    ),
    "app.quit": _action(
        "apps",
        "power",
        "#EF6A71",
        "Fermer une application",
        "Quit an application",
        "Ferme le programme indiqué.",
        "Quits the selected program.",
        capability="apps",
        arguments=(_arg("target"),),
    ),
    "window.focus": _action(
        "apps",
        "app",
        "#58B69B",
        "Afficher une fenêtre",
        "Focus a window",
        "Ramène une fenêtre ouverte au premier plan.",
        "Brings an open window to the front.",
        capability="windows",
    ),
    "obs.scene.set": _action(
        "obs",
        "video",
        "#7D73F1",
        "Changer de scène OBS",
        "Change OBS scene",
        "Passe à une scène précise dans OBS Studio.",
        "Switches to a specific OBS Studio scene.",
        capability="obs",
        arguments=(_arg("scene"),),
    ),
    "obs.stream.toggle": _action(
        "obs",
        "record",
        "#EF6A71",
        "Démarrer / arrêter le stream",
        "Start / stop stream",
        "Bascule la diffusion en direct dans OBS.",
        "Toggles live streaming in OBS.",
        capability="obs",
    ),
    "obs.record.toggle": _action(
        "obs",
        "record",
        "#EF6A71",
        "Démarrer / arrêter l’enregistrement",
        "Start / stop recording",
        "Bascule l’enregistrement dans OBS.",
        "Toggles recording in OBS.",
        capability="obs",
    ),
    "obs.source.toggle": _action(
        "obs",
        "video",
        "#7D73F1",
        "Afficher / masquer une source",
        "Show / hide a source",
        "Bascule la visibilité d’une source dans une scène.",
        "Toggles a source inside a scene.",
        capability="obs",
        arguments=(_arg("scene"), _arg("source")),
    ),
    "page.open": _action(
        "navigation",
        "page",
        "#43A6CF",
        "Ouvrir une autre page",
        "Open another page",
        "Affiche une page de boutons sur la 3DS.",
        "Opens another button page on the 3DS.",
        arguments=(_arg("page", "page"),),
    ),
    "settings.open": _action(
        "navigation",
        "gear",
        "#6D88AA",
        "Ouvrir les réglages 3DS",
        "Open 3DS settings",
        "Affiche les réglages directement sur la console.",
        "Opens settings directly on the console.",
    ),
    "modal.volumes": _action(
        "navigation",
        "volume-up",
        "#6D88AA",
        "Ouvrir le panneau des volumes",
        "Open volume panel",
        "Affiche les volumes sur la console.",
        "Shows volume controls on the console.",
    ),
    "frame.toggle": _action(
        "navigation",
        "video",
        "#6D88AA",
        "Basculer le plein écran",
        "Toggle full screen",
        "Agrandit ou réduit l’affichage supérieur.",
        "Toggles the top display full screen.",
    ),
    "system.lock": _action(
        "advanced",
        "lock",
        "#E98D54",
        "Verrouiller l’ordinateur",
        "Lock computer",
        "Verrouille immédiatement la session.",
        "Locks the current session.",
        capability="lock",
    ),
    "script.run": _action(
        "advanced",
        "terminal",
        "#E98D54",
        "Exécuter un script autorisé",
        "Run an allowed script",
        "Lance un script déclaré dans config.json.",
        "Runs a script declared in config.json.",
        arguments=(_arg("script", "script"),),
    ),
    "noop": _action(
        "advanced",
        "app",
        "#63758D",
        "Ne rien faire",
        "Do nothing",
        "Laisse volontairement le bouton sans effet.",
        "Intentionally leaves the button inactive.",
    ),
}
