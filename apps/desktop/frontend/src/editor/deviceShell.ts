import type { CSSProperties } from "react";

// SVG viewBox and apertures, in the same coordinates as device-shell.svg.
// Keep the screen sizes proportional to the console's 400×240 / 320×240.
const viewport = { width: 640, height: 680 };
const apertures = {
  top: { x: 144.7, y: 100.5, width: 351.25, height: 210.75 },
  bottom: { x: 179.85, y: 373.725, width: 281, height: 210.75 },
};

export const deviceShellStyle = {
  aspectRatio: `${viewport.width} / ${viewport.height}`,
  ...Object.fromEntries(Object.entries(apertures).flatMap(([screen, rect]) => [
    [`--${screen}-left`, `${rect.x / viewport.width * 100}%`],
    [`--${screen}-top`, `${rect.y / viewport.height * 100}%`],
    [`--${screen}-width`, `${rect.width / viewport.width * 100}%`],
    [`--${screen}-height`, `${rect.height / viewport.height * 100}%`],
  ])),
} as CSSProperties;
