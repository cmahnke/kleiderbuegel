// Generates a self-hosted VersaTiles "colorful" style (v6 API) for this site.
//
// Output (new files only, never overwrites tracked code):
//   static/map-styles/kleiderbuegel-colorful.json
//
// Conventions (kept compatible with existing, unmodified callers):
//   - source key stays "versatiles-shortbread" (as emitted by osm()),
//     so assets/js/maps/leaflet-map.js `sources["versatiles-"+style]`
//     keeps working with style="shortbread".
//   - tiles point to the projektemacher static central-europe PBFs.
//   - sprites point to local /map-styles/sprites/{base,extras,icons}
//     (vendored by scripts/versatiles.sh from the release sprites.tar.gz).
//   - glyphs stay on tiles.versatiles.org (theme renders text via webfonts;
//     vendoring glyphs is out of scope).
//
// Usage: node scripts/generate-versatiles-style.mjs [--out <path>]

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { osm } from '@versatiles/style';

const TILE_URL =
  process.env.VERSATILES_TILES_URL ??
  'https://static.projektemacher.org/maps/central-europe/tiles/{z}/{x}/{y}.pbf';
const GLYPHS_PATTERN =
  process.env.VERSATILES_GLYPHS_PATTERN ??
  'https://tiles.versatiles.org/assets/glyphs/{fontstack}/{range}.pbf';
const SPRITE_BASE =
  process.env.VERSATILES_SPRITE_BASE ?? '/map-styles/sprites';
const OUTFILE =
  process.argv.includes('--out')
    ? process.argv[process.argv.indexOf('--out') + 1]
    : 'static/map-styles/kleiderbuegel-colorful.json';

const style = osm({
  theme: 'colorful',
  text: { language: 'de' },
  urls: {
    // Empty base keeps sprite URLs site-relative (/map-styles/...)
    // instead of resolving them against tiles.versatiles.org (Node default).
    base: '',
    osm: TILE_URL,
    glyphsPattern: GLYPHS_PATTERN,
    sprite: [
      { id: 'base', url: `${SPRITE_BASE}/base` },
      { id: 'extras', url: `${SPRITE_BASE}/extras` },
      { id: 'icons', url: `${SPRITE_BASE}/icons` },
    ],
  },
});

// Raw "{z}/{x}/{y}" template => source has no TileJSON `url` reference,
// so inlineSources() would be a no-op; skip it to stay offline.
// Just restore the OSM attribution (raw templates carry none).
const source = style.sources['versatiles-shortbread'];
if (source && !source.attribution) {
  source.attribution =
    '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
}

const outPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  OUTFILE,
);
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify(style, null, 2) + '\n');
console.log(`Wrote ${OUTFILE}`);
