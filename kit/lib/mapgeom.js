/* The arithmetic under the family story's maps: an extent, a projection, a clip. No data, no Astro.
 *
 * It is separate from storymap.js so that the tool which writes kit/data/story-basemap.json
 * (kit/tools/storybasemap.mjs) and the logic selftest (kit/tools/story_logic.mjs) can use it under plain Node:
 * it imports no JSON (Vite imports JSON, Node needs an attribute), so the named extents are passed in.
 *
 * EXTENT. A map's frame is a box in degrees ({west, east, south, north}) and a projection. A name from
 * kit/data/story-extents.json stands for a box and a projection; a box written out is the same thing. The
 * Python gate (kit/tools/checkfamilystory.py) reads the same file, so "this place is inside this map" means
 * the same in both languages.
 *
 * PROJECTIONS. Three, because three is all a family story needs:
 *   equirectangular  x = (lon - west) * cos(middle latitude), y = north - lat, one scale for both. The default:
 *                    a town 20 km across looks as wide as it is tall at 45 degrees north.
 *   plate-carree     x = lon - west, y = north - lat. Degrees are degrees. Right at the equator, wide elsewhere.
 *   mercator         the navigation chart. y is the Mercator ordinate, so shapes are right and areas are not.
 * Each returns { W, H, X(lon), Y(lat) } for a picture W wide (640 by default); H follows from the box.
 */
export const PROJECTIONS = ["equirectangular", "plate-carree", "mercator"];

const RAD = Math.PI / 180;
const isNum = (v) => typeof v === "number" && Number.isFinite(v);

/* An extent as the page writes it ("europe", {preset: "europe"}, or a box) as a full box. Returns null when it is
   neither a name nor a box with west < east and south < north inside the world. */
export function resolveExtent(ext, presets = {}) {
  if (ext == null) return null;
  let name = null, box = null;
  if (typeof ext === "string") { name = ext; box = presets[ext]; }
  else if (typeof ext === "object" && typeof ext.preset === "string") { name = ext.preset; box = { ...presets[ext.preset], ...ext }; }
  else if (typeof ext === "object") box = ext;
  if (!box) return null;
  const r = { west: box.west, east: box.east, south: box.south, north: box.north, projection: box.projection || "equirectangular", name };
  if (![r.west, r.east, r.south, r.north].every(isNum)) return null;
  if (!(r.west < r.east) || !(r.south < r.north)) return null;
  if (r.west < -180 || r.east > 180 || r.south < -85 || r.north > 85) return null;
  if (!PROJECTIONS.includes(r.projection)) return null;
  return r;
}

/* Is a point inside the frame? The boundary counts. */
export const inExtent = (r, lat, lon) =>
  isNum(lat) && isNum(lon) && lon >= r.west && lon <= r.east && lat >= r.south && lat <= r.north;

const merc = (lat) => Math.log(Math.tan(Math.PI / 4 + (Math.max(-85, Math.min(85, lat)) * RAD) / 2));

export function makeProjection(r, W = 640) {
  const { west: w, east: e, south: s, north: n } = r;
  if (r.projection === "mercator") {
    const k = W / ((e - w) * RAD);
    const top = merc(n);
    return { W, H: Math.round((top - merc(s)) * k), k, X: (lon) => (lon - w) * RAD * k, Y: (lat) => (top - merc(lat)) * k,
             ux: (deg) => deg * RAD * k, uy: (deg) => deg * RAD * k };
  }
  const c0 = r.projection === "plate-carree" ? 1 : Math.cos((((s + n) / 2) * Math.PI) / 180);
  const k = W / ((e - w) * c0);
  return { W, H: Math.round((n - s) * k), k, c0, X: (lon) => (lon - w) * c0 * k, Y: (lat) => (n - lat) * k,
           ux: (deg) => deg * c0 * k, uy: (deg) => deg * k };
}

/* Sutherland-Hodgman against a box, for a ring. pad is in picture units. */
export function clipPoly(pts, box) {
  const inside = [(p) => p[0] >= box[0], (p) => p[0] <= box[2], (p) => p[1] >= box[1], (p) => p[1] <= box[3]];
  const cut = (a, b, i) => {
    const [x0, y0] = a, [x1, y1] = b;
    if (i < 2) { const xv = i === 0 ? box[0] : box[2]; const t = (xv - x0) / (x1 - x0); return [xv, y0 + t * (y1 - y0)]; }
    const yv = i === 2 ? box[1] : box[3]; const t = (yv - y0) / (y1 - y0); return [x0 + t * (x1 - x0), yv];
  };
  let out = pts;
  for (let i = 0; i < 4; i++) {
    const inp = out; out = [];
    if (!inp.length) break;
    let prev = inp[inp.length - 1];
    for (const cur of inp) {
      if (inside[i](cur)) { if (!inside[i](prev)) out.push(cut(prev, cur, i)); out.push(cur); }
      else if (inside[i](prev)) out.push(cut(prev, cur, i));
      prev = cur;
    }
  }
  return out;
}

/* A line (a border) keeps only the runs inside the box. */
export function clipLine(pts, box) {
  const runs = []; let cur = [];
  const inb = (p) => p[0] >= box[0] && p[0] <= box[2] && p[1] >= box[1] && p[1] <= box[3];
  for (const p of pts) { if (inb(p)) cur.push(p); else { if (cur.length > 1) runs.push(cur); cur = []; } }
  if (cur.length > 1) runs.push(cur);
  return runs;
}

export const r1 = (v) => Math.round(v * 10) / 10;
export const pathD = (pts, close) => (pts.length < 2 ? "" : "M" + pts.map((p) => `${r1(p[0])} ${r1(p[1])}`).join("L") + (close ? "Z" : ""));

/* The quadratic curve a leg is drawn as. `bend` swings the control point sideways, as a fraction of the chord. The line
   stops 6 units short of the far dot so the arrowhead sits on its rim. Returns the path and where its label goes. */
export function legCurve(a, b, bend = 0, lo = [0, 0]) {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2, dx = b.x - a.x, dy = b.y - a.y;
  const cx = mx - dy * bend, cy = my + dx * bend;
  const len = Math.hypot(b.x - cx, b.y - cy) || 1;
  const ex = b.x - ((b.x - cx) / len) * 6, ey = b.y - ((b.y - cy) / len) * 6;
  const lx = 0.25 * a.x + 0.5 * cx + 0.25 * ex, ly = 0.25 * a.y + 0.5 * cy + 0.25 * ey;
  return { d: `M${r1(a.x)} ${r1(a.y)}Q${r1(cx)} ${r1(cy)} ${r1(ex)} ${r1(ey)}`, lx: r1(lx + (lo[0] || 0)), ly: r1(ly + (lo[1] || 0)) };
}
