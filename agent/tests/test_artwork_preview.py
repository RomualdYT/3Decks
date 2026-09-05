"""The editor reuses cached console artwork without another remote download."""
import io
from unittest.mock import patch

import pytest
from PIL import Image

from deck3ds import artwork
from deck3ds.transports.parts import ArtworkCache


def console_texture():
    pixels = b"".join(
        bytes((255 if x < 64 else 0, 255 if y < 64 else 0, 0))
        for y in range(128) for x in range(128)
    )
    return artwork._swizzle(pixels, 3)


def test_preview_preserves_console_colors_and_orientation():
    image = Image.open(io.BytesIO(artwork.preview_png(console_texture())))
    assert image.size == (128, 128)
    assert image.getpixel((0, 0)) == (255, 255, 0)
    assert image.getpixel((127, 0)) == (0, 255, 0)
    assert image.getpixel((0, 127)) == (255, 0, 0)
    assert image.getpixel((127, 127)) == (0, 0, 0)
    with pytest.raises(ValueError):
        artwork.preview_png(b"invalid")


def test_artwork_cache_prepares_preview_once_and_clears_it():
    cache = ArtworkCache()
    with patch.object(artwork, "download", return_value=b"image") as download, patch.object(
        artwork, "to_texture", return_value=console_texture()
    ):
        assert cache.update("https://example.test/cover.png")
        first = cache.preview()
        assert first and first.startswith(b"\x89PNG")
        assert not cache.update("https://example.test/cover.png")
        assert cache.preview() is first
        download.assert_called_once()
        assert cache.update("")
        assert cache.preview() is None


@pytest.mark.asyncio
async def test_artwork_endpoint_reads_only_cached_bytes(client, agent):
    assert (await client.get("/api/artwork")).status_code == 204
    image = artwork.preview_png(console_texture())
    agent._artwork._preview = image
    with patch.object(artwork, "download", side_effect=AssertionError("HTTP must not download")):
        response = await client.get("/api/artwork")
    assert response.content == image
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert (await client.get("/api/artwork", headers={"X-Deck3DS-Token": ""})).status_code == 403
