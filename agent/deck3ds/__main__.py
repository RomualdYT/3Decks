"""Point d'entrée de l'agent Deck3DS.

Usage :
    python3 -m deck3ds                      démarre avec config.json
    python3 -m deck3ds --config autre.json  fichier de configuration explicite
    python3 -m deck3ds --check              valide la configuration et quitte
    python3 -m deck3ds --probe              teste les capacités de la machine
    python3 -m deck3ds --ui                 ouvre l'interface de configuration
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from . import config as config_module
from .platforms.base import Platform
from .server import VERSION, Server

#: Port de l'interface locale. Voisin de celui de la console (38123) pour rester
#: mémorisable, tout en restant distinct : l'interface n'écoute que sur la
#: boucle locale, la console sur le réseau.
DEFAULT_UI_PORT = 38124


def build_platform() -> Platform:
    """Choisit l'adaptateur correspondant au système hôte."""
    if sys.platform == "darwin":
        from .platforms.macos import MacPlatform

        return MacPlatform()

    if sys.platform in ("win32", "cygwin"):
        from .platforms.windows import WindowsPlatform

        return WindowsPlatform()

    # Aucun adaptateur : l'agent démarre quand même, mais les actions
    # échoueront avec un message explicite plutôt qu'en silence.
    print(
        f"Attention : plateforme '{sys.platform}' non prise en charge, "
        "les actions systeme seront indisponibles.",
        file=sys.stderr,
    )
    return Platform()


def default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config.json"


def _open_browser(url: str) -> None:
    """Ouvre l'interface dans le navigateur par défaut.

    Importé ici et non au sommet : `webbrowser` sonde l'environnement graphique
    au chargement, ce qui est inutile pour un agent lancé sans interface.
    """
    import webbrowser

    webbrowser.open(url)


def command_probe() -> int:
    """Affiche ce que la machine sait réellement faire.

    Utile avant de configurer les boutons : inutile de placer un bouton micro
    si l'état du micro n'est pas accessible sur ce poste.
    """
    platform = build_platform()
    print(f"Agent Deck3DS {VERSION}")
    print(f"Plateforme detectee : {platform.name} ({sys.platform})")
    print()

    snapshot = platform.snapshot()

    def show(label: str, value: object, unit: str = "") -> None:
        if value is None or value == "" or value == []:
            print(f"  {label:<22} indisponible")
        else:
            print(f"  {label:<22} {value}{unit}")

    print("Lecture de l'etat :")
    show("volume", snapshot.volume, " %")
    show("son coupe", snapshot.muted)
    show("micro coupe", snapshot.mic_muted)
    show("processeur", snapshot.cpu, " %")
    show("memoire", snapshot.memory, " %")
    show("application active", snapshot.active_app)
    show("applications", len(snapshot.apps) or None)

    if snapshot.media is not None:
        show("media", f"{snapshot.media.title} — {snapshot.media.artist}")
        show("lecteur", snapshot.media.app)
    else:
        show("media", None)

    if snapshot.apps:
        print()
        print("Applications visibles :")
        for name in snapshot.apps:
            print(f"  - {name}")

    print()
    if snapshot.mic_muted is None:
        print(
            "Note : l'etat du micro n'est pas lisible sur ce poste. Le bouton\n"
            "       fonctionnera, mais l'ecran affichera « MICRO ? » jusqu'au\n"
            "       premier basculement."
        )
    if snapshot.media is None:
        print(
            "Note : aucun media detecte. Sur macOS, autorisez l'application\n"
            "       Terminal a piloter Spotify ou Musique dans Reglages Systeme,\n"
            "       rubrique Confidentialite et securite, puis Automatisation."
        )
    return 0


def command_check(path: Path) -> int:
    try:
        loaded = config_module.load(path)
    except config_module.ConfigError as error:
        print(f"Configuration invalide : {error}", file=sys.stderr)
        return 1

    print(f"Configuration valide : {path}")
    print(f"  revision      : {loaded.revision}")
    print(f"  ecoute        : {loaded.host}:{loaded.port}")
    print(f"  jeton         : {'oui' if loaded.token else 'non'}")
    print(f"  rafraichissement : {loaded.poll_interval} s")
    print(f"  pas de volume : {loaded.volume_step}")
    print(f"  pages         : {len(loaded.pages)}")

    for page in loaded.pages:
        print(
            f"    - {page.id} ({page.title('en')}), "
            f"tableau de bord « {page.dashboard} »"
        )
        for button in sorted(page.buttons, key=lambda item: item.slot):
            action = button.action.kind
            details = ""
            if button.action.args:
                details = " " + ", ".join(
                    f"{key}={value}" for key, value in button.action.args.items()
                )
            hold = ""
            if button.hold_action is not None:
                hold = f", appui long : {button.hold_action.kind}"
            print(
                f"        [{button.slot}] {button.label('en'):<14} "
                f"{action}{details}{hold}"
            )

    if loaded.scripts:
        print("  scripts declares :")
        for name, command in loaded.scripts.items():
            print(f"    - {name}: {' '.join(command)}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="deck3ds",
        description="Agent PC pour Deck3DS : transforme une 3DS en surface "
        "de controle.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path(),
        help="chemin du fichier de configuration (defaut : config.json)",
    )
    parser.add_argument(
        "--host", help="adresse d'ecoute, remplace celle de la configuration"
    )
    parser.add_argument(
        "--port", type=int, help="port d'ecoute, remplace celui de la configuration"
    )
    parser.add_argument(
        "--check", action="store_true", help="valide la configuration et quitte"
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="teste les capacites de la machine et quitte",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="ouvre l'interface de configuration locale dans le navigateur",
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=DEFAULT_UI_PORT,
        help=f"port de l'interface locale (defaut : {DEFAULT_UI_PORT})",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="journalisation detaillee"
    )
    parser.add_argument("--version", action="version", version=f"deck3ds {VERSION}")

    args = parser.parse_args(argv)

    if args.probe:
        return command_probe()

    if args.check:
        return command_check(args.config)

    try:
        loaded = config_module.load(args.config)
    except config_module.ConfigError as error:
        print(f"Configuration invalide : {error}", file=sys.stderr)
        print(
            "Verifiez le fichier avec : python3 -m deck3ds --check",
            file=sys.stderr,
        )
        return 1

    if args.host:
        loaded.host = args.host
    if args.port:
        loaded.port = args.port

    platform = build_platform()
    server = Server(
        loaded,
        platform,
        verbose=args.verbose,
        config_path=args.config,
        ui_port=args.ui_port if args.ui else None,
    )

    if args.ui:
        # L'ouverture est différée : le navigateur ne doit atteindre le serveur
        # qu'une fois celui-ci en écoute, sinon la page affiche une erreur.
        server.on_ui_ready = _open_browser

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print()
        print("Agent arrete.")

    close = getattr(platform, "close", None)
    if callable(close):
        close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
