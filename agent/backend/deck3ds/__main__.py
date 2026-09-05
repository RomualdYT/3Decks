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
import os
import sys
from pathlib import Path

from . import config as config_module
from .configuration.location import default_config_path, initialize
from .platforms.base import Platform
from .runtime.signals import run_agent
from .runtime.factory import build_platform, create_runtime
from .transports.parts import Options as ServerOptions
from .version import VERSION

#: Port de l'interface locale. Voisin de celui de la console (38123) pour rester
#: mémorisable, tout en restant distinct : l'interface n'écoute que sur la
#: boucle locale, la console sur le réseau.
DEFAULT_UI_PORT = 38124


def _open_browser(url: str) -> None:
    """Ouvre l'interface dans le navigateur par défaut.

    Importé ici et non au sommet : `webbrowser` sonde l'environnement graphique
    au chargement, ce qui est inutile pour un agent lancé sans interface.
    """
    import webbrowser

    print(f"Interface de configuration : {url}", flush=True)
    webbrowser.open(url)


def command_probe() -> int:
    """Affiche ce que la machine sait réellement faire.

    Utile avant de configurer les boutons : inutile de placer un bouton micro
    si l'état du micro n'est pas accessible sur ce poste.
    """
    platform = build_platform()
    try:
        return _probe(platform)
    finally:
        platform.close()


def _probe(platform: Platform) -> int:
    print(f"Agent 3Decks {VERSION}")
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
    notification_status = platform.notification_status()
    show(
        "notifications",
        notification_status["access"] if notification_status["available"] else None,
    )

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
        if sys.platform == "darwin":
            print(
                "Note : aucun media detecte. Autorisez l'application Terminal\n"
                "       a piloter Spotify ou Musique dans Reglages Systeme,\n"
                "       rubrique Confidentialite et securite, puis Automatisation."
            )
        else:
            print(
                "Note : aucun media detecte. Lancez une lecture dans une application\n"
                "       compatible avec les controles media de Windows."
            )
    if sys.platform in ("win32", "cygwin") and not notification_status["available"]:
        print(
            "Note : les notifications Windows exigent l'installation MSIX et\n"
            "       l'autorisation UserNotificationListener. Aucun acces de\n"
            "       secours a la base SQLite de Windows n'est utilise."
        )
        if notification_status["error"]:
            print(f"       Detail : {notification_status['error']}")
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
        description="Agent PC pour 3Decks : transforme une 3DS en surface "
        "de controle.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="configuration explicite (sinon depot historique ou repertoire utilisateur)",
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
        "--init-config",
        action="store_true",
        help="cree une configuration de demonstration, sans ecraser de fichier",
    )
    parser.add_argument(
        "--init-if-missing",
        action="store_true",
        help="cree la configuration si elle manque, puis continue le demarrage",
    )
    parser.add_argument(
        "--ui-dev-origin",
        action="append",
        default=[],
        help="autorise explicitement une origine Vite locale, par exemple http://127.0.0.1:4173",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="journalisation detaillee"
    )
    parser.add_argument("--desktop", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--stop", action="store_true", help="arrete proprement l'instance graphique et attend sa fermeture")
    parser.add_argument(
        "--background",
        action="store_true",
        help="demarre l'interface sans ouvrir automatiquement le navigateur",
    )
    parser.add_argument("--version", action="version", version=f"deck3ds {VERSION}")

    args = parser.parse_args(argv)
    args.config = (
        args.config.expanduser().resolve() if args.config else default_config_path()
    )
    if args.stop:
        from .desktop.instance import InstanceLock

        if InstanceLock.for_config(args.config).request_stop():
            return 0
        print("3Decks est encore en cours d'arret. Reessayez une fois ses operations terminees.", file=sys.stderr)
        return 1
    from .api.security import local_origin

    try:
        for origin in args.ui_dev_origin:
            local_origin(origin)
    except ValueError as error:
        parser.error(str(error))

    if args.init_config:
        try:
            initialize(args.config)
        except (OSError, config_module.ConfigError) as error:
            print(f"Creation impossible : {error}", file=sys.stderr)
            return 1
        print(f"Configuration creee : {args.config}")
        return 0

    if args.init_if_missing and not args.config.exists():
        try:
            initialize(args.config)
        except FileExistsError:
            # Une autre instance a pu terminer l'initialisation entre le test
            # et l'ecriture exclusive. Le chargement ci-dessous reste
            # l'autorite qui validera le document obtenu.
            pass
        except (OSError, config_module.ConfigError) as error:
            print(f"Creation impossible : {error}", file=sys.stderr)
            return 1
        else:
            print(f"Configuration creee : {args.config}")

    if args.probe:
        return command_probe()

    if args.check:
        return command_check(args.config)

    try:
        loaded = config_module.load(args.config)
    except config_module.ConfigError as error:
        print(f"Configuration invalide : {error}", file=sys.stderr)
        print(
            "Creez une configuration avec deck3ds --init-config, ou verifiez-la avec --check.",
            file=sys.stderr,
        )
        return 1

    if args.host:
        loaded.host = args.host
    if args.port:
        loaded.port = args.port

    server = create_runtime(
        loaded,
        ServerOptions(
            verbose=args.verbose,
            config_path=args.config,
            ui_port=args.ui_port if args.ui else None,
            ui_dev_origins=tuple(args.ui_dev_origin),
        ),
    )

    if args.desktop and sys.platform in {"darwin", "win32", "cygwin"}:
        from .desktop import DesktopOptions, run_desktop
        from .desktop.logging import configure_desktop_logging
        from .desktop.models import LaunchSpec

        packaged_launcher = os.environ.get("DECK3DS_DESKTOP_LAUNCHER", "")
        if packaged_launcher:
            python = Path(packaged_launcher).resolve()
            launch_arguments = ["--background"]
        else:
            python = Path(sys.executable).resolve()
            if sys.platform in {"win32", "cygwin"} and python.name.lower() == "python.exe":
                pythonw = python.with_name("pythonw.exe")
                if pythonw.is_file():
                    python = pythonw
            launch_arguments = [
                "-m",
                "deck3ds",
                "--init-if-missing",
                "--ui",
                "--desktop",
                "--background",
                "--config",
                str(args.config),
                "--ui-port",
                str(args.ui_port),
            ]
            if args.host:
                launch_arguments.extend(("--host", args.host))
            if args.port:
                launch_arguments.extend(("--port", str(args.port)))
            if args.verbose:
                launch_arguments.append("--verbose")
            for origin in args.ui_dev_origin:
                launch_arguments.extend(("--ui-dev-origin", origin))
        log_path = configure_desktop_logging()
        return run_desktop(
            server,
            DesktopOptions(
                launch=LaunchSpec(
                    executable=python,
                    arguments=tuple(launch_arguments),
                    working_directory=args.config.parent,
                ),
                log_path=log_path,
                open_browser=not args.background,
            ),
        )

    if args.ui and not args.background:
        # L'ouverture est différée : le navigateur ne doit atteindre le serveur
        # qu'une fois celui-ci en écoute, sinon la page affiche une erreur.
        server.on_ui_ready = _open_browser

    try:
        asyncio.run(run_agent(server))
    except KeyboardInterrupt:
        print()
        print("Agent arrete.")

    return 0


def ui_main() -> int:
    """Entry point sans console pour le raccourci installe sur le bureau."""
    return main(["--init-if-missing", "--ui", "--desktop", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
