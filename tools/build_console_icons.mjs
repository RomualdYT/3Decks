#!/usr/bin/env node
/** Build native-size 3DS atlases from the exact Lucide components used on PC. */
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync, copyFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
const root = resolve(import.meta.dirname, '..');
const requireFrontend = createRequire(join(root, 'apps/desktop/frontend/package.json'));
const React = requireFrontend('react');
const { renderToStaticMarkup } = requireFrontend('react-dom/server');
const Lucide = requireFrontend('lucide-react');
const manifest = readFileSync(join(root, 'apps/console/source/graphics/icon_assets.def'), 'utf8');
const definitions = [...manifest.matchAll(/^ICON_ASSET\((\w+), ([\w-]+)\)$/gm)]
  .map((match) => ({ id: match[1], name: match[2] }));
const deckSource = readFileSync(join(root, 'apps/desktop/frontend/src/components/DeckIcon.tsx'), 'utf8');
const mappingSource = deckSource.match(/const ICONS:[\s\S]*?= \{([\s\S]*?)\n\};/)?.[1];
if (!mappingSource || definitions.length !== 22) throw new Error('Icon catalog is incomplete');
const desktopIcons = new Map([...mappingSource.matchAll(/(?:"([\w-]+)"|\b([\w-]+)):\s*(\w+)/g)]
  .map((match) => [match[1] ?? match[2], match[3]]));
const sizesSource = readFileSync(join(root, 'apps/console/source/graphics/icon_sizes.def'), 'utf8');
const sizes = [...sizesSource.matchAll(/^ICON_SIZE\((\d+)\)$/gm)]
  .map((match) => Number(match[1]));
if (sizes.length < 2 || sizes.some((size, index) =>
  size < 8 || size > 64 || (index > 0 && size <= sizes[index - 1]))) {
  throw new Error('Icon sizes must be increasing and within the 3DS sprite range');
}
const work = mkdtempSync(join(tmpdir(), '3decks-icons-'));
try {
  for (const size of sizes) {
    const folder = join(work, String(size));
    mkdirSync(folder);
    const files = [];
    for (const [index, { id, name }] of definitions.entries()) {
      const componentName = desktopIcons.get(name);
      const Icon = Lucide[componentName];
      if (typeof Icon !== 'object' && typeof Icon !== 'function') {
        throw new Error(`Missing desktop Lucide component for ${id}: ${name}`);
      }
      const basename = `${String(index).padStart(2, '0')}-${name}`;
      // White shape + alpha coverage: Citro2D applies each button's state color.
      const svg = renderToStaticMarkup(React.createElement(Icon, {
        size, color: '#ffffff', strokeWidth: 1.9,
      }));
      writeFileSync(join(folder, `${basename}.svg`), svg);
      files.push(`${basename}.png`);
    }
    writeFileSync(join(folder, 'icons.t3s'), `--atlas -f rgba8888 -z auto\n${files.join('\n')}\n`);
  }
  execFileSync('docker', [
    'run', '--rm', '--entrypoint', 'sh', '-v', `${work}:/work`,
    '3decks-console-packaging:local', '-c',
    'set -eu; for dir in /work/*/; do for svg in "$dir"*.svg; do rsvg-convert "$svg" -o "${svg%.svg}.png"; done; (cd "$dir" && tex3ds -i icons.t3s -o "/work/icons-$(basename "$dir").t3x" -H "/work/icons-$(basename "$dir").h"); done',
  ], { stdio: 'inherit', timeout: 180_000 });
  for (const size of sizes) {
    const header = readFileSync(join(work, `icons-${size}.h`), 'utf8');
    const indices = [...header.matchAll(/^#define \w+_idx (\d+)$/gm)]
      .map((match) => Number(match[1]));
    if (indices.length !== definitions.length ||
        indices.some((index, position) => index !== position)) {
      throw new Error(`Unexpected icon order in ${size}px atlas`);
    }
  }
  const output = join(root, 'apps/console/romfs/icons');
  mkdirSync(output, { recursive: true });
  for (const size of sizes) copyFileSync(join(work, `icons-${size}.t3x`), join(output, `icons-${size}.t3x`));
  console.log(`Generated ${sizes.length} atlases × ${definitions.length} icons`);
} finally {
  rmSync(work, { recursive: true, force: true });
}
