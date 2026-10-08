# Shared assets

This reference is for contributors changing generated resources. Ordinary builds
use the checked-in assets and do not need to regenerate them.

## Community invitation

`community.json` is the shared source for the Discord invitation. After changing
it, regenerate the desktop QR, frontend constant and console QR matrix:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install qrcode==8.2
.venv/bin/python tools/build_community_qr.py
```

On Windows, use `.venv/Scripts/python.exe`. Commit the three generated files with
`community.json`; retain the QR quiet zone for scanning.

## Console preview shell

The editable asset is `apps/desktop/frontend/public/device-shell.svg`.
Its proportions were reconstructed from [New 3DS XL Vector by
Epsiilon2048](https://www.reddit.com/r/3DS/comments/c8u702/new_3ds_xl_black_vector_art/).
Keep this source attribution when changing the shell.

The SVG uses a 640 × 680 viewBox. Keep both screen apertures aligned with
`apps/desktop/frontend/src/editor/deviceShell.ts` and their 400 × 240 / 320 × 240
aspect ratios. `ConsoleTouchCanvas.tsx` scales the touch content separately.
Decorative animation must respect reduced-motion preferences.

## Decky, fonts and icons

- Decky's original geometry: `apps/console/source/graphics/decky.c`.
- Desktop sprite: `tools/export_decky_sprite.c`.
- Header logo and README banners: `tools/export_decky_brand.c`.
- HOME artwork: `apps/console/packaging/generate_artwork.sh`.
- Native font faces: `tools/make-font.sh`.
- Spotify mark: `tools/make-brand-icons.sh`.
- Console Lucide atlases: `tools/build_console_icons.mjs`.

Exporter source headers document their commands. See the
[console README](../apps/console/README.md) and
[packaging guide](../docs/CONSOLE_PACKAGING.md) for dependencies and regeneration.
Keep generated assets, their source definitions and third-party licence notices together.
