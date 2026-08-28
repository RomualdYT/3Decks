"""Catalogue des touches assignables à un raccourci.

Ce module est l'unique source de vérité pour les raccourcis clavier. Il existe
pour résoudre trois défauts précis du fonctionnement précédent, où chaque
adaptateur portait sa propre table :

1. **Les deux tables divergeaient.** Une touche acceptée sur un système pouvait
   être refusée sur l'autre, alors qu'un fichier de configuration est censé
   être portable. Ici, une touche déclare ses deux codes côte à côte : en
   ajouter une sur un seul système devient impossible.

2. **Aucune validation à l'enregistrement.** `ctrl+alt+banane` était accepté par
   l'éditeur et n'échouait qu'à l'appui du bouton, sur la console — le pire
   endroit pour l'apprendre. `parse_hotkey` permet de refuser en amont.

3. **La langue servait de clé.** Les graphies françaises étaient empilées dans la
   table (`echap`, `echappement`, `entree`...), mélangeant identité et
   présentation. Ici l'identifiant est stable et non traduit ; les langues ne
   servent qu'à l'affichage, et les anciennes graphies survivent comme alias.

Les codes des touches non imprimables sont positionnels et stables : ils ne
dépendent pas de la disposition du clavier. Ceux de macOS ont été vérifiés en
interrogeant `UCKeyTranslate`, qui ne leur associe aucun caractère imprimable.

Les lettres et les chiffres ne figurent pas dans la table : ils sont acceptés
directement (`a`, `7`) et résolus par chaque adaptateur.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Key:
    """Une touche non imprimable, et sa traduction sur chaque système.

    `mac` est un keycode Carbon (`key code` en AppleScript), `win` un code
    virtuel Windows (`VK_*`). Les deux sont positionnels.
    """

    name: str
    mac: int
    win: int
    label_en: str
    label_fr: str
    group: str
    #: Anciennes graphies acceptées, pour ne pas invalider les configurations
    #: déjà écrites. Elles ne sont jamais proposées par l'interface.
    aliases: tuple[str, ...] = ()


#: Regroupements présentés par l'interface, dans cet ordre.
GROUPS = ("editing", "navigation", "function")


#: Touches assignables. L'ordre est celui de l'affichage.
KEYS: tuple[Key, ...] = (
    # --- Édition ---
    Key("escape", 53, 0x1B, "Escape", "Échap", "editing", ("esc", "echap", "echappement")),
    Key("return", 36, 0x0D, "Return", "Entrée", "editing", ("enter", "entree", "retour")),
    Key("tab", 48, 0x09, "Tab", "Tabulation", "editing", ("tabulation",)),
    Key("space", 49, 0x20, "Space", "Espace", "editing", ("espace",)),
    # `delete` efface à gauche sur macOS (touche Retour arrière) comme
    # `backspace` sur Windows : ce sont bien les mêmes positions.
    Key("backspace", 51, 0x08, "Backspace", "Retour arrière", "editing", ("delete",)),
    # La touche « Suppr » d'un clavier étendu, qui efface à droite.
    Key("forward_delete", 117, 0x2E, "Delete", "Suppr", "editing",
        ("suppr", "supprimer")),
    # --- Navigation ---
    Key("left", 123, 0x25, "Left", "Gauche", "navigation", ("gauche",)),
    Key("right", 124, 0x27, "Right", "Droite", "navigation", ("droite",)),
    Key("up", 126, 0x26, "Up", "Haut", "navigation", ("haut",)),
    Key("down", 125, 0x28, "Down", "Bas", "navigation", ("bas",)),
    Key("home", 115, 0x24, "Home", "Début", "navigation", ("debut",)),
    Key("end", 119, 0x23, "End", "Fin", "navigation", ("fin",)),
    Key("pageup", 116, 0x21, "Page Up", "Page préc.", "navigation", ()),
    Key("pagedown", 121, 0x22, "Page Down", "Page suiv.", "navigation", ()),
    # macOS n'a pas de touche d'impression d'écran ; les claviers Windows la
    # présentent comme F13 lorsqu'ils sont branchés sur un Mac. C'est le plus
    # proche équivalent, et cela préserve les configurations Windows existantes.
    Key("printscreen", 105, 0x2C, "Print Screen", "Impr. écran", "navigation", ()),
    # --- Touches de fonction ---
    # Les codes macOS ne suivent aucune progression : ils sont énumérés.
    Key("f1", 122, 0x70, "F1", "F1", "function", ()),
    Key("f2", 120, 0x71, "F2", "F2", "function", ()),
    Key("f3", 99, 0x72, "F3", "F3", "function", ()),
    Key("f4", 118, 0x73, "F4", "F4", "function", ()),
    Key("f5", 96, 0x74, "F5", "F5", "function", ()),
    Key("f6", 97, 0x75, "F6", "F6", "function", ()),
    Key("f7", 98, 0x76, "F7", "F7", "function", ()),
    Key("f8", 100, 0x77, "F8", "F8", "function", ()),
    Key("f9", 101, 0x78, "F9", "F9", "function", ()),
    Key("f10", 109, 0x79, "F10", "F10", "function", ()),
    Key("f11", 103, 0x7A, "F11", "F11", "function", ()),
    Key("f12", 111, 0x7B, "F12", "F12", "function", ()),
)


@dataclass(frozen=True)
class Modifier:
    """Touche de modification, et sa traduction sur chaque système.

    `mac` est la formulation attendue par AppleScript, `win` un code virtuel.
    """

    name: str
    mac: str
    win: int
    label_en: str
    label_fr: str
    aliases: tuple[str, ...] = ()


#: Modificateurs assignables, dans l'ordre d'affichage et d'écriture.
#:
#: Une combinaison est toujours normalisée dans cet ordre, afin que
#: `shift+cmd+a` et `cmd+shift+a` produisent le même texte.
MODIFIERS: tuple[Modifier, ...] = (
    # `cmd` n'existe pas sur Windows : la touche Windows en tient lieu, comme
    # c'est l'usage dans les raccourcis équivalents.
    Modifier("cmd", "command down", 0x5B, "Cmd", "Cmd", ("command", "win", "super", "meta")),
    Modifier("ctrl", "control down", 0x11, "Ctrl", "Ctrl", ("control",)),
    Modifier("alt", "option down", 0x12, "Alt", "Alt", ("opt", "option")),
    Modifier("shift", "shift down", 0x10, "Shift", "Maj", ()),
)


def _index(items, extract) -> dict:
    """Table de correspondance nom canonique et alias vers l'élément."""
    table = {}
    for item in items:
        for key in (item.name, *item.aliases):
            table[key] = extract(item)
    return table


#: Résolution d'un nom (canonique ou historique) vers sa touche.
BY_NAME: dict[str, Key] = _index(KEYS, lambda key: key)

#: Idem pour les modificateurs.
MODIFIER_BY_NAME: dict[str, Modifier] = _index(MODIFIERS, lambda mod: mod)


class InvalidHotkey(ValueError):
    """Combinaison refusée, avec un message destiné à l'utilisateur."""


@dataclass(frozen=True)
class Hotkey:
    """Combinaison analysée, prête à être envoyée au système."""

    #: Modificateurs, triés selon l'ordre de `MODIFIERS`.
    modifiers: tuple[Modifier, ...] = ()
    #: Touche non imprimable visée, si la combinaison en désigne une.
    key: Key | None = None
    #: Caractère visé, lorsque la combinaison porte une lettre ou un chiffre.
    character: str = ""

    def canonical(self) -> str:
        """Écriture normalisée, telle qu'enregistrée dans la configuration."""
        names = [modifier.name for modifier in self.modifiers]
        names.append(self.key.name if self.key is not None else self.character)
        return "+".join(names)

    def label(self, locale: str = "en") -> str:
        """Écriture lisible, pour l'interface."""
        parts = [
            modifier.label_fr if locale == "fr" else modifier.label_en
            for modifier in self.modifiers
        ]
        if self.key is not None:
            parts.append(self.key.label_fr if locale == "fr" else self.key.label_en)
        else:
            parts.append(self.character.upper())
        return " + ".join(parts)


def parse_hotkey(text: str) -> Hotkey:
    """Analyse une combinaison écrite `cmd+shift+a`.

    Lève `InvalidHotkey` avec un message explicite : cette fonction sert autant
    à exécuter le raccourci qu'à le refuser dans l'éditeur, ce qui garantit que
    les deux appliquent exactement la même règle.
    """
    if not isinstance(text, str):
        raise InvalidHotkey("un texte est attendu")

    parts = [part.strip().lower() for part in text.split("+") if part.strip()]
    if not parts:
        raise InvalidHotkey("combinaison vide")

    modifiers: list[Modifier] = []
    remaining: list[str] = []
    for part in parts:
        modifier = MODIFIER_BY_NAME.get(part)
        # Un modificateur répété est ignoré plutôt que refusé : `cmd+cmd+a`
        # exprime sans ambiguïté la même intention que `cmd+a`.
        if modifier is not None:
            if modifier not in modifiers:
                modifiers.append(modifier)
        else:
            remaining.append(part)

    if not remaining:
        raise InvalidHotkey(
            "une touche est attendue en plus des modificateurs"
        )
    if len(remaining) > 1:
        raise InvalidHotkey(
            f"une seule touche est attendue, {len(remaining)} trouvées: "
            + ", ".join(remaining)
        )

    modifiers.sort(key=MODIFIERS.index)
    target = remaining[0]

    key = BY_NAME.get(target)
    if key is not None:
        return Hotkey(tuple(modifiers), key=key)

    # Lettre ou chiffre : accepté tel quel, chaque système le résout selon la
    # disposition active du clavier.
    if len(target) == 1 and (target.isalnum() or target.isprintable()):
        return Hotkey(tuple(modifiers), character=target)

    raise InvalidHotkey(f"touche inconnue: {target}")


def catalog(locale: str = "en") -> dict:
    """Description du catalogue, pour l'interface de configuration.

    L'éditeur web s'en sert pour proposer les touches assignables au lieu de
    laisser l'utilisateur les deviner, et n'a ainsi aucune table à dupliquer.
    """
    return {
        "modifiers": [
            {
                "name": modifier.name,
                "label": modifier.label_fr if locale == "fr" else modifier.label_en,
                "label_en": modifier.label_en,
                "label_fr": modifier.label_fr,
            }
            for modifier in MODIFIERS
        ],
        "groups": list(GROUPS),
        "keys": [
            {
                "name": key.name,
                "label": key.label_fr if locale == "fr" else key.label_en,
                "label_en": key.label_en,
                "label_fr": key.label_fr,
                "group": key.group,
            }
            for key in KEYS
        ],
    }
