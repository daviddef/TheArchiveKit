#!/usr/bin/env node
/* Write kit/data/story-basemap.json: the coastline and national borders of the family story's regional maps,
 * simplified and clipped, so a map of "europe" does not decode, simplify and clip the whole planet to draw one page.
 *
 *   node kit/tools/storybasemap.mjs --write     regenerate kit/data/story-basemap.json from outlines.json
 *   node kit/tools/storybasemap.mjs --check     fail when the file is not what --write would make (the kit's test)
 *
 * SOURCE. kit/data/outlines.json, which is Natural Earth 1:50m land and national borders (public domain,
 * naturalearthdata.com). Nothing is drawn here that Natural Earth did not draw; it is only simplified (Douglas-Peucker,
 * to about a picture pixel at 640 wide) and cut to each layer's box. The layers are the named extents in
 * kit/data/story-extents.json; a map whose box is far smaller than any layer (a county) is not served from here but from
 * outlines.json at 50m, in storymap.js, because a layer simplified for a continent would have flattened it.
 *
 * ENCODING. Integer hundredths of a degree, delta-encoded from each ring's first point, the same idea as outlines.json
 * (which is thousandths): [x0, y0, dx1, dy1, ...]. Nothing here reaches a reader: the component turns it into one SVG
 * path per map at build time.
 *
 * It decodes and simplifies by itself rather than importing kit/lib/outlines.js, because that file imports its JSON the
 * way Vite does and a plain Node script cannot.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { clipPoly, clipLine } from "../lib/mapgeom.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, "..", "data");
const OUT = path.join(DATA, "story-basemap.json");
const SC = 100;

const raw = JSON.parse(fs.readFileSync(path.join(DATA, "outlines.json"), "utf8"));
const ext = JSON.parse(fs.readFileSync(path.join(DATA, "story-extents.json"), "utf8")).extents;
const RS = raw.scale || 1000;

function decode(d) {
  let x = d[0], y = d[1]; const pts = [[x / RS, y / RS]];
  for (let i = 2; i < d.length; i += 2) { x += d[i]; y += d[i + 1]; pts.push([x / RS, y / RS]); }
  return pts;
}
function bbox(pts) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of pts) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  return [x0, y0, x1, y1];
}
function dp(pts, tol) {
  if (pts.length < 3 || tol <= 0) return pts;
  const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1;
  const st = [[0, pts.length - 1]];
  while (st.length) {
    const [a, b] = st.pop(); let far = -1, best = tol;
    const [ax, ay] = pts[a], [bx, by] = pts[b]; const dx = bx - ax, dy = by - ay; const den = Math.hypot(dx, dy) || 1;
    for (let i = a + 1; i < b; i++) { const dist = Math.abs(dy * pts[i][0] - dx * pts[i][1] + bx * ay - by * ax) / den; if (dist > best) { best = dist; far = i; } }
    if (far > 0) { keep[far] = 1; st.push([a, far], [far, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}
function simplifyRing(pts, tol) {
  const n = pts.length; if (n < 4) return pts;
  let far = 1, best = -1;
  for (let i = 1; i < n - 1; i++) { const d = Math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]); if (d > best) { best = d; far = i; } }
  return dp(pts.slice(0, far + 1), tol).concat(dp(pts.slice(far), tol).slice(1));
}
function encode(pts) {
  const q = pts.map(([x, y]) => [Math.round(x * SC), Math.round(y * SC)]);
  const out = [q[0][0], q[0][1]]; let px = q[0][0], py = q[0][1];
  for (let i = 1; i < q.length; i++) { out.push(q[i][0] - px, q[i][1] - py); px = q[i][0]; py = q[i][1]; }
  return out;
}

export function build() {
  const layers = {};
  for (const [name, b] of Object.entries(ext)) {
    const m = 1;                                   /* a degree of margin, so a coast is not cut at the frame's edge */
    const box = [b.west - m, b.south - m, b.east + m, b.north + m];
    const tol = Math.max(0.01, (b.east - b.west) / 700);
    const pick = (set, close) => {
      const out = [];
      for (const d of set) {
        const pts = decode(d); const [x0, y0, x1, y1] = bbox(pts);
        if (x1 < box[0] || x0 > box[2] || y1 < box[1] || y0 > box[3]) continue;
        const s = simplifyRing(pts, tol);
        const cut = close ? [clipPoly(s, box)] : clipLine(s, box);
        for (const c of cut) if (c.length >= (close ? 3 : 2)) out.push(encode(c));
      }
      return out;
    };
    layers[name] = { box: [b.west, b.south, b.east, b.north], tol: Math.round(tol * 1000) / 1000, land: pick(raw.land, true), borders: pick(raw.borders, false) };
  }
  return {
    note: "Coastline and national borders for the family story's regional maps, simplified and cut to each extent in story-extents.json. Written by kit/tools/storybasemap.mjs from outlines.json; do not edit. Build-time only: nothing here reaches a reader except the one SVG path per map that the component draws from it.",
    source: "Natural Earth 1:50m Admin 0 countries and land (naturalearthdata.com), through outlines.json",
    licence: "Public domain. Natural Earth asks for no credit; the map's caption gives it anyway.",
    scale: SC,
    layers,
  };
}

const text = () => JSON.stringify(build()) + "\n";

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const arg = process.argv[2];
  if (arg === "--write") {
    const t = text(); fs.writeFileSync(OUT, t);
    const b = JSON.parse(t);
    console.log(`storybasemap: wrote ${path.relative(process.cwd(), OUT)} (${(t.length / 1024).toFixed(0)} KB)`);
    for (const [k, l] of Object.entries(b.layers)) console.log(`  ${k.padEnd(20)} land ${String(l.land.length).padStart(4)}  borders ${String(l.borders.length).padStart(4)}  tol ${l.tol}`);
  } else if (arg === "--check") {
    const have = fs.existsSync(OUT) ? fs.readFileSync(OUT, "utf8") : "";
    if (have !== text()) { console.error("storybasemap: kit/data/story-basemap.json is not what outlines.json and story-extents.json make. Run: node kit/tools/storybasemap.mjs --write"); process.exit(1); }
    console.log("storybasemap: ok, story-basemap.json matches outlines.json and story-extents.json");
  } else { console.error("usage: storybasemap.mjs --write | --check"); process.exit(2); }
}
