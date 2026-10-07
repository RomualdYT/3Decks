# Shared assets

## Community invitation

`community.json` is the source for the Discord invitation used by both apps.
After changing the URL, regenerate the desktop QR, frontend constant and console
QR matrix from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install qrcode==8.2
.venv/bin/python tools/build_community_qr.py
```

Commit the three generated files with `community.json`. Generated QR assets
include the quiet zone required for scanning.

## Console preview

The editable shell is `apps/desktop/frontend/public/device-shell.svg`.
Its proportions were reconstructed from [New 3DS XL Vector by
Epsiilon2048](https://www.reddit.com/r/3DS/comments/c8u702/new_3ds_xl_black_vector_art/).

The SVG uses a 640 × 680 coordinate system. Keep its screen apertures aligned
with `apps/desktop/frontend/src/editor/deviceShell.ts`. `ConsoleTouchCanvas.tsx`
scales the interactive touch-screen content separately; SVG `foreignObject`
caused cropping in WebKit.

The amber LED animation is decorative and respects reduced-motion preferences.
