import json
import zipfile
from pathlib import Path

import pytest

from tools.release_assets import png_ico, render, sha256


def _wheel(path: Path, version: str = "1.2.3") -> Path:
    wheel = path / f"deck3ds-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"deck3ds-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.3\nName: deck3ds\nVersion: {version}\n",
        )
    return wheel


def _png(width: int = 192, height: int = 170) -> bytes:
    # Only the signature and IHDR dimensions are inspected by the ICO wrapper.
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\0\0\0\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"test"
    )


def test_release_assets_are_immutable_verified_and_user_facing(tmp_path):
    wheel = _wheel(tmp_path)
    icon = tmp_path / "logo.png"
    icon.write_bytes(_png())
    output = tmp_path / "release"

    manifest = render(
        wheel=wheel,
        output=output,
        repository="RomualdYT/3Decks",
        tag="v1.2.3",
        icon=icon,
    )

    assert manifest["version"] == "1.2.3"
    assert manifest["wheel"] == {"name": wheel.name, "sha256": sha256(wheel)}
    assert json.loads((output / "release.json").read_text())["tag"] == "v1.2.3"
    assert (output / "3decks.ico").read_bytes()[:6] == b"\0\0\1\0\1\0"
    assert (output / "install-3decks-macos.sh").stat().st_mode & 0o111

    for name in ("install-3decks-macos.sh", "install-3decks-windows.ps1"):
        installer = (output / name).read_text(encoding="utf-8")
        assert "__" not in installer
        assert "v1.2.3" in installer
        assert sha256(wheel) in installer
        assert "--init-if-missing" in installer
        assert "tool install --python 3.12 --force" in installer

    macos = (output / "install-3decks-macos.sh").read_text(encoding="utf-8")
    assert 'DECK3DS_DESKTOP_LAUNCHER="$0"' in macos
    assert 'exec "$DECK3DS_UI" "$@"' in macos

    checksums = (output / "SHA256SUMS.txt").read_text(encoding="utf-8")
    assert "SHA256SUMS.txt" not in checksums
    for path in output.iterdir():
        if path.name != "SHA256SUMS.txt":
            assert f"{sha256(path)}  {path.name}" in checksums

    # Re-rendering a release is deterministic and never hashes a previous
    # checksum file into its replacement.
    previous = checksums
    render(
        wheel=wheel,
        output=output,
        repository="RomualdYT/3Decks",
        tag="v1.2.3",
        icon=icon,
    )
    assert (output / "SHA256SUMS.txt").read_text(encoding="utf-8") == previous


@pytest.mark.parametrize(
    ("repository", "tag"),
    [("not-a-repository", "v1.2.3"), ("owner/repo", "latest")],
)
def test_release_assets_reject_ambiguous_sources(tmp_path, repository, tag):
    wheel = _wheel(tmp_path)
    icon = tmp_path / "logo.png"
    icon.write_bytes(_png())
    with pytest.raises(ValueError):
        render(
            wheel=wheel,
            output=tmp_path / "release",
            repository=repository,
            tag=tag,
            icon=icon,
        )


def test_release_tag_must_match_wheel_metadata(tmp_path):
    wheel = _wheel(tmp_path)
    icon = tmp_path / "logo.png"
    icon.write_bytes(_png())
    with pytest.raises(ValueError, match="does not match"):
        render(
            wheel=wheel,
            output=tmp_path / "release",
            repository="owner/repo",
            tag="v1.2.4",
            icon=icon,
        )


def test_ico_wrapper_rejects_invalid_or_oversized_png():
    with pytest.raises(ValueError, match="not a PNG"):
        png_ico(b"no")
    with pytest.raises(ValueError, match="dimensions"):
        png_ico(_png(512, 512))
