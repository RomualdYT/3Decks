# Nintendo 3DS / 2DS application

The native C client discovers the computer over UDP and communicates through
framed TCP messages. `source/` contains the application, `tests/` contains host
tests, `romfs/` contains bundled resources, and `packaging/` contains HOME Menu
package assets.

From the repository root:

```sh
bash tools/test_console.sh
./build.sh all
```

The first command uses a local C compiler. The `.3dsx` and `.cia` build uses
Docker and devkitPro. See the [build guide](../../docs/CONSOLE_PACKAGING.md),
[architecture](../../docs/CONSOLE_ARCHITECTURE.md), and
[protocol](../../docs/PROTOCOL.md). [Français](README.fr.md).

## Console typography

Inter is rasterized separately at six native cell heights: 13, 14, 15, 17, 20
and 24 pixels. `source/graphics/font_faces.def` is shared by the renderer and
generator. Run `./tools/make-font.sh` from the repository root to rebuild the
six BCFNT assets using a digest-pinned devkitPro image. The generator validates
cell heights before replacing the assets. Assets are checked in; ordinary
builds do not regenerate them.

Citro2D normalizes fonts to 30 pixels, so each style uses `native_height / 30`
without another correction. Native textures are sampled one texel per screen
pixel, preserving the font's baked antialiasing at integer positions. Parsed
text cache keys include both label and font face. Missing or mismatched assets
fall back to the legacy font, then the system font. Arbitrary scales retain
legacy smooth filtering.

The native family adds approximately 3 MiB of textures and bundled resources.
Host tests cover sizes, alignment, font changes in the cache, fallback and
resource cleanup. Final readability still needs assessment on physical screens,
especially small labels and secondary information under reflections.

## Brand icons

The Spotify mark is rasterized at its native 16 × 16 pixel size from
`packaging/brands/spotify.svg`, then stored as RGBA8 in RomFS. Antialiasing is
baked into the texture; rendering uses a 1:1 scale and pixel alignment after
the stereo offset.

Regenerate it from the repository root:

```sh
docker build -t 3decks-console-packaging:local -f apps/console/packaging/Dockerfile .
bash tools/make-brand-icons.sh
```

The `.t3x` asset is versioned, so regular builds require no SVG rasterization.
A generic music icon is used if loading fails.

## Console button icons

The 22 console icons use the same Lucide components and 1.9 px stroke as
`frontend/src/components/DeckIcon.tsx`. `source/graphics/icon_assets.def` maps
console IDs to desktop names and fixes atlas order. Six RGBA atlases cover native
sizes from 12 to 52 pixels; Citro2D applies each button's live color and state.
The old primitives remain a fallback if an atlas cannot load.

After changing the desktop icons or their mapping, regenerate and commit the
atlases with `node tools/build_console_icons.mjs`. This needs the desktop
frontend dependencies and the console packaging Docker image described above.
The generator checks that the indices emitted by tex3ds match the manifest.
Lucide's license is included in `packaging/icons/LUCIDE-LICENSE`.
