/* One map of a family's moves, as data a component can draw: base map, dots, legs. Build time only.
 *
 * Takes a map from the story data (kit/docs/story.md: {id, title, extent, places, legs, regions}) and returns paths and
 * points in a picture 640 units wide. The arithmetic is in mapgeom.js; this file chooses the coastline.
 *
 * WHICH COASTLINE. Natural Earth, public domain, two ways:
 *   - a named region (or any box) whose width is at least a sixth of a layer in story-basemap.json that contains it is
 *     drawn from that layer, already simplified for a picture that size;
 *   - a box smaller than that (a county, the road from a village to its coast) is drawn from the 50m outlines in
 *     outlines.json, simplified to a picture pixel, because a layer made for a continent would flatten it.
 * Either way the rings are clipped to the picture, so a frame that touches Eurasia does not ship Eurasia.
 *
 * LEGS. solid = documented, dashed = inferred, dotted = family memory. A leg whose route is not known (routeKnown: false)
 * is NOT drawn: a line between two dots says someone went that way, and the papers say only that they came from there.
 * It stays in the list under the map, marked "route not known", so the claim is still made, in words.
 */
import EXT from "../data/story-extents.json";
import BASE from "../data/story-basemap.json";
import { outlinesIn } from "./outlines.js";
import { resolveExtent, makeProjection, clipPoly, clipLine, pathD, legCurve, r1 } from "./mapgeom.js";

export const extentOf = (ext) => resolveExtent(ext, EXT.extents);

const SC = BASE.scale || 100;
function decode(dd) { let x = dd[0], y = dd[1]; const pts = [[x / SC, y / SC]]; for (let i = 2; i < dd.length; i += 2) { x += dd[i]; y += dd[i + 1]; pts.push([x / SC, y / SC]); } return pts; }

/* The smallest layer that holds the box and is not enormously bigger than it. */
export function layerFor(r) {
  let best = null, bestW = Infinity;
  for (const [name, l] of Object.entries(BASE.layers)) {
    const [w, s, e, n] = l.box;
    if (r.west < w || r.east > e || r.south < s || r.north > n) continue;
    if ((r.east - r.west) < (e - w) / 6) continue;
    if (e - w < bestW) { best = name; bestW = e - w; }
  }
  return best;
}

export function geometryFor(r) {
  const layer = layerFor(r);
  if (layer) { const l = BASE.layers[layer]; return { source: layer, land: l.land.map(decode), borders: l.borders.map(decode) }; }
  const o = outlinesIn({ w: r.west - 1, e: r.east + 1, s: r.south - 1, n: r.north + 1 }, (r.east - r.west) / 260);
  return { source: "outlines", land: o.land, borders: o.borders };
}

export const GRADE_WORD = { doc: "documented", inf: "inferred", lore: "family memory" };
const LEG_CLASS = { doc: "solid", inf: "dashed", lore: "dotted" };

export function buildMap(map, W = 640) {
  const r = extentOf(map.extent);
  if (!r) throw new Error(`story map ${map.id}: its extent is neither a name from story-extents.json nor a box`);
  const P = makeProjection(r, W);
  const pad = 12, box = [-pad, -pad, P.W + pad, P.H + pad];
  const g = geometryFor(r);
  const proj = (ring) => ring.map(([lon, lat]) => [P.X(lon), P.Y(lat)]);
  const land = g.land.map((q) => clipPoly(proj(q), box)).filter((q) => q.length > 2).map((q) => pathD(q, true)).join("");
  const borders = g.borders.flatMap((q) => clipLine(proj(q), box)).map((q) => pathD(q, false)).join("");

  const places = {};
  for (const p of map.places || []) places[p.id] = { ...p, x: P.X(p.lon), y: P.Y(p.lat) };
  const legs = (map.legs || []).map((L) => {
    const a = places[L.from], b = places[L.to];
    const known = L.routeKnown !== false;
    const curve = a && b && known ? legCurve(a, b, L.bend || 0, L.labelOffset || [0, 0]) : null;
    return { ...L, a, b, known, cls: LEG_CLASS[L.grade] || "dotted", word: GRADE_WORD[L.grade] || "family memory", curve };
  });
  const regions = (map.regions || []).map((q) => ({
    ...q, x: P.X(q.lon), y: P.Y(q.lat), rx: q.radius > 0 ? P.ux(q.radius) * 1.6 : 0, ry: q.radius > 0 ? P.uy(q.radius) : 0,
  }));
  return { extent: r, P, W: P.W, H: P.H, source: g.source, land, borders, places, legs, regions };
}

export { r1 };
