#!/usr/bin/env python3
"""Envoi d'un fichier .3dsx vers une 3DS par Wi-Fi (protocole 3dslink).

Réimplémentation autonome de `3dslink`, en Python et sans dépendance. Elle
existe pour deux raisons :

- l'outil `3dslink` fourni par devkitPro est un binaire Linux ; utilisé depuis un
  conteneur, il ne peut ni émettre ni recevoir les diffusions réseau du réseau
  local, ce qui empêche la découverte automatique de la console ;
- disposer du protocole en Python permet de découvrir la console, d'envoyer le
  fichier et d'afficher la progression sans rien installer.

Protocole, tel qu'implémenté par le Homebrew Launcher :

  1. découverte, facultative : datagramme « 3dsboot » diffusé sur le port 17491,
     la console répond « boot3ds » ;
  2. connexion TCP sur le port 17491 ;
  3. longueur du nom de fichier (4 octets, little-endian) puis le nom ;
  4. taille du fichier compressé (4 octets) ;
  5. attente d'un accusé de réception (4 octets, 0 pour accepter) ;
  6. données compressées en zlib, par blocs précédés de leur taille ;
  7. second accusé de réception ;
  8. longueur des arguments (4 octets) puis les arguments, séparés par des
     octets nuls.

Usage :
    python3 tools/send3ds.py                      découverte automatique
    python3 tools/send3ds.py -a 192.168.1.32      adresse explicite
    python3 tools/send3ds.py --scan               liste les consoles trouvées
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys
import time
import zlib
from pathlib import Path

#: Port d'écoute du netloader sur la console.
LINK_PORT = 17491

#: Message de découverte et réponse attendue.
PROBE = b"3dsboot"
REPLY = b"boot3ds"

#: Taille des blocs compressés. Valeur retenue par l'implémentation d'origine.
CHUNK_SIZE = 16 * 1024

#: Codes d'erreur renvoyés par la console.
ERRORS = {
    -1: "erreur interne de la console",
    -2: "espace insuffisant sur la carte SD",
    -3: "la console a refuse le transfert",
}


def discover(timeout: float = 4.0, verbose: bool = True) -> list[str]:
    """Diffuse une annonce et retourne les adresses des consoles qui répondent.

    La console doit être en attente : dans le Homebrew Launcher, elle écoute en
    permanence, il n'y a donc rien à activer manuellement.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # SO_REUSEPORT permet à plusieurs programmes d'écouter le même port, ce qui
    # évite un échec quand un autre outil de transfert tourne déjà.
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass

    try:
        # Se lier au port permet de recevoir la réponse, la console répondant
        # vers ce même numéro de port.
        sock.bind(("", LINK_PORT))
    except OSError:
        # Port déjà pris : on continue sans liaison explicite, la réponse
        # arrivera sur un port éphémère si la console le tolère.
        pass

    sock.settimeout(0.4)

    found: list[str] = []
    deadline = time.monotonic() + timeout
    attempt = 0

    if verbose:
        print("Recherche de la console sur le reseau local...")

    while time.monotonic() < deadline:
        attempt += 1
        for address in _broadcast_addresses():
            try:
                sock.sendto(PROBE, (address, LINK_PORT))
            except OSError:
                continue

        try:
            while True:
                data, sender = sock.recvfrom(256)
                if data.startswith(REPLY) and sender[0] not in found:
                    found.append(sender[0])
                    if verbose:
                        print(f"  console trouvee : {sender[0]}")
        except socket.timeout:
            pass

        if found:
            break

    sock.close()
    return found


def _broadcast_addresses() -> list[str]:
    """Adresses de diffusion à essayer.

    La diffusion générale est parfois filtrée ; on ajoute la diffusion dirigée
    du sous-réseau local, mieux acceptée par certains routeurs.
    """
    addresses = ["255.255.255.255"]

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        local = probe.getsockname()[0]
        probe.close()

        parts = local.split(".")
        if len(parts) == 4:
            addresses.append(f"{parts[0]}.{parts[1]}.{parts[2]}.255")
    except OSError:
        pass

    return addresses


def _netload_token(address: str) -> str:
    """Construit l'argument transportant l'adresse de l'ordinateur émetteur.

    `libctru` inspecte le dernier argument transmis et, s'il mesure exactement
    17 caractères et contient `_3DSLINK_` à partir du neuvième, il le retire de
    `argv` et renseigne `__3dslink_host` avec les huit premiers caractères lus
    comme un entier hexadécimal.

    Cet entier est l'adresse au format réseau, tel que le produit `inet_addr` :
    le premier octet de l'adresse occupe donc les bits de poids faible.

    Ainsi, l'application connaît l'adresse du poste sans que l'utilisateur ait
    à la saisir.
    """
    octets = [int(part) for part in address.split(".")]
    if len(octets) != 4 or any(value < 0 or value > 255 for value in octets):
        raise ValueError(f"adresse IPv4 invalide : {address}")

    # Ordre réseau : a.b.c.d devient 0xddccbbaa une fois relu en petit-boutiste.
    value = (
        octets[0] | (octets[1] << 8) | (octets[2] << 16) | (octets[3] << 24)
    )
    return f"{value:08X}_3DSLINK_"


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    """Lit exactement `size` octets, ou lève une erreur."""
    chunks = bytearray()
    while len(chunks) < size:
        block = sock.recv(size - len(chunks))
        if not block:
            raise ConnectionError("la console a ferme la connexion")
        chunks.extend(block)
    return bytes(chunks)


def _read_response(sock: socket.socket, step: str) -> None:
    """Lit un accusé de réception et convertit un code négatif en erreur."""
    (code,) = struct.unpack("<i", _recv_exact(sock, 4))
    if code != 0:
        raise RuntimeError(f"{step} : {ERRORS.get(code, f'code {code}')}")


def send(
    path: Path,
    address: str,
    args: list[str] | None = None,
    verbose: bool = True,
) -> None:
    """Envoie `path` vers la console située à `address`."""
    payload = path.read_bytes()
    name = path.name

    # La compression réduit nettement le temps de transfert : le Wi-Fi de la
    # console est le facteur limitant, pas la décompression.
    compressed = zlib.compress(payload, 6)

    if verbose:
        ratio = 100.0 * len(compressed) / max(1, len(payload))
        print(f"Envoi de {name} vers {address}:{LINK_PORT}")
        print(
            f"  {len(payload) / 1024:.0f} Ko compresses en "
            f"{len(compressed) / 1024:.0f} Ko ({ratio:.0f} %)",
            flush=True,
        )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)

    try:
        sock.connect((address, LINK_PORT))
    except OSError as error:
        raise RuntimeError(
            f"connexion impossible vers {address}:{LINK_PORT} ({error}).\n"
            "Verifiez que la console est bien dans le Homebrew Launcher."
        ) from error

    try:
        encoded_name = name.encode("utf-8")
        sock.sendall(struct.pack("<i", len(encoded_name)))
        sock.sendall(encoded_name)
        sock.sendall(struct.pack("<i", len(compressed)))

        # La console valide le nom et réserve la place avant tout transfert.
        _read_response(sock, "preparation refusee")

        sent = 0
        while sent < len(compressed):
            chunk = compressed[sent : sent + CHUNK_SIZE]
            sock.sendall(struct.pack("<i", len(chunk)))
            sock.sendall(chunk)
            sent += len(chunk)

            if verbose:
                percent = 100.0 * sent / len(compressed)
                bar = int(percent / 2.5)
                print(
                    f"\r  [{'#' * bar}{'.' * (40 - bar)}] {percent:5.1f} %",
                    end="",
                    flush=True,
                )

        if verbose:
            print()

        _read_response(sock, "transfert refuse")

        # Adresse locale de l'interface effectivement utilisée pour joindre la
        # console : c'est celle que l'application devra contacter.
        local_ip = sock.getsockname()[0]

        # Arguments : le premier est le nom du programme, comme pour argv. Le
        # dernier transporte l'adresse de cet ordinateur (voir _netload_token).
        argv = [name] + (args or []) + [_netload_token(local_ip)]
        blob = b"".join(item.encode("utf-8") + b"\0" for item in argv)
        sock.sendall(struct.pack("<i", len(blob)))
        sock.sendall(blob)

        if verbose:
            print(f"Transfert termine. Adresse transmise : {local_ip}")
            print("L'application demarre sur la console.")
    finally:
        sock.close()


def default_binary() -> Path:
    return Path(__file__).resolve().parent.parent / "3ds-app" / "deck3ds.3dsx"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="send3ds",
        description="Envoie un fichier .3dsx vers une 3DS par Wi-Fi, "
        "sans passer par la carte SD.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        default=default_binary(),
        help="fichier .3dsx a envoyer (defaut : 3ds-app/deck3ds.3dsx)",
    )
    parser.add_argument(
        "-a", "--address", help="adresse de la console, sinon recherche automatique"
    )
    parser.add_argument(
        "--scan", action="store_true", help="cherche les consoles et quitte"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="duree de la recherche en secondes (defaut : 5)",
    )
    parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help="argument transmis a l'application, repetable",
    )

    options = parser.parse_args(argv)

    if options.scan:
        found = discover(options.timeout)
        if not found:
            print()
            print("Aucune console trouvee.")
            print("Verifiez que :")
            print("  - la console est allumee et dans le Homebrew Launcher ;")
            print("  - elle est sur le meme reseau Wi-Fi que cet ordinateur ;")
            print("  - le reseau n'isole pas les appareils entre eux.")
            return 1
        print()
        print(f"{len(found)} console(s) : {', '.join(found)}")
        return 0

    if not options.file.exists():
        print(f"Fichier introuvable : {options.file}", file=sys.stderr)
        print("Compilez d'abord avec : ./build.sh", file=sys.stderr)
        return 1

    address = options.address
    if not address:
        found = discover(options.timeout)
        if not found:
            print()
            print("Aucune console trouvee.", file=sys.stderr)
            print(
                "Indiquez l'adresse manuellement : "
                "python3 tools/send3ds.py -a 192.168.1.32",
                file=sys.stderr,
            )
            print(
                "L'adresse de la console figure dans les parametres Internet "
                "de la 3DS.",
                file=sys.stderr,
            )
            return 1
        address = found[0]
        print()

    try:
        send(options.file, address, options.arg)
    except (RuntimeError, ConnectionError, OSError) as error:
        print()
        print(f"Echec : {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
