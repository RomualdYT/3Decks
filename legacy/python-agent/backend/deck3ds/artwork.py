"""Préparation des pochettes d'album pour l'écran de la console.

L'image est convertie dans le format attendu par le processeur graphique de la
3DS, afin que la console n'ait aucun travail de décodage à fournir : elle
téléverse le bloc reçu directement en mémoire vidéo.

Format produit : RGB565 little-endian, réorganisé en tuiles de 8 × 8 pixels
selon l'ordre de Morton. Cet agencement a été vérifié en comparant la sortie de
`tex3ds`, l'outil officiel, sur une image témoin dont chaque pixel encodait sa
position.

Aucune bibliothèque externe n'est nécessaire : `sips`, présent sur toute
installation de macOS, effectue le redimensionnement, et le décodage TIFF non
compressé est fait ici.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from __future__ import annotations

import base64
import io
import os
import struct
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

#: Côté de la pochette envoyée. Une puissance de deux est nécessaire pour une
#: texture 3DS, et 128 offre un bon compromis entre netteté et volume (32 Ko).
ART_SIZE = 128

#: Signature identifiant une trame de pochette.
ART_MAGIC = b"ART0"

#: Délai maximal de téléchargement. Au-delà, on renonce sans bloquer l'agent.
DOWNLOAD_TIMEOUT = 6.0


def _morton_table() -> list[int]:
    """Index de chaque pixel dans une tuile de 8 × 8.

    L'index vaut l'entrelacement des bits de `x` et `y` : bit 0 de x, bit 0 de
    y, bit 1 de x, et ainsi de suite.
    """
    table = [0] * 64
    for y in range(8):
        for x in range(8):
            value = 0
            for bit in range(3):
                value |= ((x >> bit) & 1) << (2 * bit)
                value |= ((y >> bit) & 1) << (2 * bit + 1)
            table[y * 8 + x] = value
    return table


_MORTON = _morton_table()

#: Table de conversion 8 bits vers 5 bits, calculée une fois.
_TO5 = bytes(value >> 3 for value in range(256))
#: Table de conversion 8 bits vers 6 bits.
_TO6 = bytes(value >> 2 for value in range(256))


def download(url: str) -> bytes | None:
    """Télécharge une image. Retourne `None` en cas d'échec."""
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "Deck3DS/0.1"}
        )
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            # Une pochette dépasse rarement quelques centaines de kilooctets ;
            # la borne évite qu'une URL inattendue sature la mémoire.
            return response.read(4 * 1024 * 1024)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _read_tiff_pixels(path: Path) -> tuple[bytes, int] | None:
    """Extrait les pixels d'un TIFF non compressé.

    On se limite volontairement au sous-ensemble que produit `sips` avec
    l'option `formatOptions none` : bandes uniques, sans compression.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if len(data) < 8:
        return None

    if data[:2] == b"MM":
        order = ">"
    elif data[:2] == b"II":
        order = "<"
    else:
        return None

    try:
        (ifd_offset,) = struct.unpack_from(order + "I", data, 4)
        (count,) = struct.unpack_from(order + "H", data, ifd_offset)

        tags: dict[int, int] = {}
        for index in range(count):
            entry = ifd_offset + 2 + index * 12
            tag, kind, quantity = struct.unpack_from(order + "HHI", data, entry)
            if kind == 3 and quantity == 1:
                (value,) = struct.unpack_from(order + "H", data, entry + 8)
            else:
                (value,) = struct.unpack_from(order + "I", data, entry + 8)
            tags[tag] = value
    except struct.error:
        return None

    if tags.get(259, 1) != 1:
        return None  # compressé : hors du sous-ensemble géré

    samples = tags.get(277, 3)
    if samples not in (3, 4):
        return None

    offset = tags.get(273)
    if offset is None:
        return None

    needed = ART_SIZE * ART_SIZE * samples
    if offset + needed > len(data):
        return None

    return data[offset : offset + needed], samples


def to_texture(image: bytes) -> bytes | None:
    """Convertit une image quelconque au format de texture de la console.

    Retourne `ART_SIZE * ART_SIZE * 2` octets, ou `None` si la conversion
    échoue.
    """
    with tempfile.TemporaryDirectory(prefix="deck3ds-art-") as folder:
        source = Path(folder) / "source"
        target = Path(folder) / "resized.tiff"
        source.write_bytes(image)

        if os.name == "nt":
            pixels = _resize_windows(source, Path(folder) / "resized.bgr")
            return _swizzle(pixels, 3) if pixels is not None else None

        try:
            # `sips` redimensionne puis produit un TIFF non compressé, bien plus
            # simple à décoder qu'un PNG et sans dépendance supplémentaire.
            completed = subprocess.run(
                [
                    "sips",
                    "-z",
                    str(ART_SIZE),
                    str(ART_SIZE),
                    "-s",
                    "format",
                    "tiff",
                    "-s",
                    "formatOptions",
                    "none",
                    str(source),
                    "--out",
                    str(target),
                ],
                capture_output=True,
                timeout=10.0,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        if completed.returncode != 0 or not target.exists():
            return None

        decoded = _read_tiff_pixels(target)
        if decoded is None:
            return None

    pixels, samples = decoded
    return _swizzle(pixels, samples)


def _resize_windows(source: Path, target: Path) -> bytes | None:
    """Redimensionne avec System.Drawing et retourne des pixels RGB linéaires."""
    source_text = str(source).replace("'", "''")
    target_text = str(target).replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Drawing
$source=[System.Drawing.Image]::FromFile('{source_text}')
$bitmap=New-Object System.Drawing.Bitmap {ART_SIZE},{ART_SIZE},([System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$graphics=[System.Drawing.Graphics]::FromImage($bitmap)
$graphics.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.PixelOffsetMode=[System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$graphics.DrawImage($source,0,0,{ART_SIZE},{ART_SIZE})
$rectangle=New-Object System.Drawing.Rectangle 0,0,{ART_SIZE},{ART_SIZE}
$data=$bitmap.LockBits($rectangle,[System.Drawing.Imaging.ImageLockMode]::ReadOnly,[System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$length=[Math]::Abs($data.Stride)*{ART_SIZE}
$bytes=New-Object byte[] $length
[Runtime.InteropServices.Marshal]::Copy($data.Scan0,$bytes,0,$length)
[IO.File]::WriteAllBytes('{target_text}',$bytes)
$bitmap.UnlockBits($data)
$graphics.Dispose(); $bitmap.Dispose(); $source.Dispose()
"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded,
            ],
            capture_output=True,
            timeout=10.0,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 or not target.exists():
        return None
    try:
        bgr = target.read_bytes()
    except OSError:
        return None
    expected = ART_SIZE * ART_SIZE * 3
    if len(bgr) != expected:
        return None
    rgb = bytearray(expected)
    for offset in range(0, expected, 3):
        rgb[offset] = bgr[offset + 2]
        rgb[offset + 1] = bgr[offset + 1]
        rgb[offset + 2] = bgr[offset]
    return bytes(rgb)


def _swizzle(pixels: bytes, samples: int) -> bytes:
    """Réorganise des pixels linéaires en tuiles RGB565 pour le processeur 3DS."""
    output = bytearray(ART_SIZE * ART_SIZE * 2)
    tiles_per_row = ART_SIZE // 8

    for y in range(ART_SIZE):
        tile_y = y >> 3
        inner_y = (y & 7) * 8
        row = y * ART_SIZE * samples

        for x in range(ART_SIZE):
            source = row + x * samples
            red = pixels[source]
            green = pixels[source + 1]
            blue = pixels[source + 2]

            value = (_TO5[red] << 11) | (_TO6[green] << 5) | _TO5[blue]

            tile = tile_y * tiles_per_row + (x >> 3)
            destination = (tile * 64 + _MORTON[inner_y + (x & 7)]) * 2

            output[destination] = value & 0xFF
            output[destination + 1] = value >> 8

    return bytes(output)


def frame(texture: bytes, token: int) -> bytes:
    """Construit la charge utile d'une trame de pochette."""
    return (
        ART_MAGIC
        + struct.pack("<HHI", ART_SIZE, ART_SIZE, token & 0xFFFFFFFF)
        + texture
    )


def preview_png(texture: bytes) -> bytes:
    """Encode the exact cached console pixels once, off the HTTP/render loop."""
    from PIL import Image

    if len(texture) != ART_SIZE * ART_SIZE * 2:
        raise ValueError("Invalid console texture size")
    pixels = bytearray(ART_SIZE * ART_SIZE * 3)
    for y in range(ART_SIZE):
        for x in range(ART_SIZE):
            tile = (y // 8) * (ART_SIZE // 8) + x // 8
            offset = (tile * 64 + _MORTON[(y % 8) * 8 + x % 8]) * 2
            value = texture[offset] | texture[offset + 1] << 8
            target = (y * ART_SIZE + x) * 3
            pixels[target:target + 3] = bytes((
                ((value >> 11) & 31) * 255 // 31,
                ((value >> 5) & 63) * 255 // 63,
                (value & 31) * 255 // 31,
            ))
    image = Image.frombytes("RGB", (ART_SIZE, ART_SIZE), bytes(pixels))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def token_for(url: str) -> int:
    """Jeton stable identifiant une pochette.

    Deux URL identiques produisent le même jeton, ce qui permet à l'agent de ne
    retransmettre l'image que lorsqu'elle change réellement.
    """
    # Somme de contrôle simple et déterministe, indépendante du hasard
    # d'exécution contrairement à `hash`.
    import zlib

    return zlib.crc32(url.encode("utf-8")) & 0x7FFFFFFF
