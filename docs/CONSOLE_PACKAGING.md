# Console packages and HOME-menu artwork

[Documentation](README.md) · [Français](CONSOLE_PACKAGING.fr.md)

## Choose a format

| File | Use |
|---|---|
| `deck3ds.cia` | Install with FBI on a console with custom firmware, then launch from HOME. |
| `deck3ds.3dsx` | Launch from Homebrew Launcher or send using 3dslink. No HOME installation. |

Both formats use the same C application and embedded Inter font. The CIA is a real
application, not a forwarder: it does **not** require a `.3dsx` on the SD card.
They share `sdmc:/3ds/deck3ds/settings.cfg`, including pairing and preferences.
Back up this file privately; it contains the console credential.

## Install on HOME

1. Download `deck3ds.cia` from a trusted 3Decks release.
2. Copy it to `sdmc:/cias/deck3ds.cia` (create `cias` if needed).
3. In FBI, open **SD → cias → deck3ds.cia → Install CIA** and confirm.
4. Return to HOME, unwrap the new application if prompted, and open **3Decks**.

Selecting the application shows Decky's icon and the charcoal/green banner on
the upper screen. The banner is static and intentionally silent; Decky's short
wake-up animation runs **inside** the app after launch.

This requires an already configured custom-firmware console (for example,
Luma3DS). Merely copying a CIA onto the SD card does not install it. 3dslink
transfers `.3dsx` programs; it cannot install a CIA. This project does not install
custom firmware or bypass the system's installer confirmations.

To update, install the newer CIA over the existing title. Do not uninstall first.
To remove it, use the console's **System Settings → Data Management → Nintendo
3DS → Software**. Shared settings under `sdmc:/3ds/deck3ds/` remain on the SD card;
removing those settings separately also removes the console's stored pairing.

## Build

From the repository root, with Docker running:

```sh
./build.sh          # 3DSX, as before
./build.sh cia      # CIA and 3DSX
./build.sh all      # both formats
```

The packaging image adds source-built [makerom](https://github.com/3DSGuy/Project_CTR)
and [bannertool](https://github.com/diasurgical/bannertool), pinned to commits in
[the Dockerfile](../packaging/3ds/Dockerfile). No Nintendo SDK or private signing
keys are needed. These are unsigned homebrew packages, not official Nintendo
software. The base devkitPro image and Debian package repository remain rolling
dependencies; this is not a promise of bit-identical builds over time.

For a local devkitPro installation, `make -C 3ds-app cia` or `release` also needs
makerom, bannertool and Python 3 in PATH. The checked-in PNGs let normal `make`
build the 3DSX without those packaging tools.

The title ID is **`000400000F3D3C00`**, declared in
[application.rsf](../packaging/3ds/application.rsf). Keep it stable for updates.
It is a private homebrew identifier, not an allocated Nintendo title ID; no
global collision-free registry is assumed. Forks must choose their own ID and
update the package checker. Never overwrite another installed title using this ID.

Releases encode `vMAJOR.MINOR.PATCH` as `major × 1024 + minor × 16 + patch`.
Limits are 63, 63 and 15 respectively; invalid or prerelease tags fail explicitly.
For local builds, `APP_VERSION=16 ./build.sh cia` overrides the default value 1.
The release workflow derives it automatically from the tag.

## Artwork and verification

The original pixel geometry lives in `3ds-app/source/graphics/decky.c`.
[The exporter](../tools/export_home_menu.c) creates a 48 × 48 icon and a 256 × 128
banner; librsvg renders their text using the repository's Inter font. To regenerate:

```sh
docker run --rm -v "$PWD":/repo -w /repo 3decks-console-packaging:local \
  bash packaging/3ds/generate_artwork.sh
```

Use `--check` to verify the PNGs without replacing them. App artwork follows the
project license; Inter's license remains in [the font directory](../tools/fonts).
Upstream packaging-tool source and licenses remain in the build image.

CIA builds check the title ID, executable section hashes, bundled icon,
banner and font. ELF system calls are compared against RSF permissions to catch
missing kernel access. CI builds all formats and tests corrupted package rejection.

Before publishing, additionally test on real hardware: installation, icon/banner,
launch, first pairing, SD settings persistence, network discovery, audio, HOME
suspend/resume, lid sleep/wake, START exit and updating over the previous CIA.
Host checks do not prove firmware compatibility or replace these device tests.
