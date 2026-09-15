/* Coastlines and national borders, decoded at BUILD TIME and never shipped.
 *
 * Natural Earth 50m, public domain, rounded to thousandths of a degree — about
 * 110 metres, which is finer than any frame these archives draw. Stored as
 * integer deltas from each ring's first point, which is what takes it from
 * 2.4 MB of GeoJSON to 600 KB.
 *
 * Only the rings that INTERSECT a given frame are decoded and emitted, so a
 * page showing one mountain county ships that county's coast and nothing else.
 * The reader never downloads a world atlas to look at Senj.
 */
import RAW from "../data/outlines.json";

const SC = RAW.scale || 1000;

function decode(d) {
  let x = d[0], y = d[1];
  const pts = [[x / SC, y / SC]];
  for (let i = 2; i < d.length; i += 2) {
    x += d[i]; y += d[i + 1];
    pts.push([x / SC, y / SC]);
  }
  return pts;
}

/* A ring is kept when its bounding box overlaps the frame. Cheap, and at these
   scales there is no ring big enough for the box to be a bad proxy except
   Antarctica and Eurasia, which are only ever drawn when you are looking at
   them anyway. */
function bbox(d) {
  let x = d[0], y = d[1], x0 = x, x1 = x, y0 = y, y1 = y;
  for (let i = 2; i < d.length; i += 2) {
    x += d[i]; y += d[i + 1];
    if (x < x0) x0 = x; else if (x > x1) x1 = x;
    if (y < y0) y0 = y; else if (y > y1) y1 = y;
  }
  return [x0 / SC, y0 / SC, x1 / SC, y1 / SC];
}

/* Douglas–Peucker, so a frame two degrees wide does not carry vertices it
   cannot resolve. tol is in degrees.
 *
 * A CLOSED RING CANNOT BE FED TO THIS DIRECTLY. Its first and last points are
 * the same, so the baseline between them has no direction, every perpendicular
 * distance computes as zero, and the whole coastline collapses to a single
 * point — which is exactly what the first version of this drew: four paths
 * reading "M202.4 165.6 L202.4 165.6". Split the ring at the vertex farthest
 * from its start and simplify the two open chains.
 */
function simplifyRing(pts, tol) {
  const n = pts.length;
  const closed = n > 3 && pts[0][0] === pts[n - 1][0] && pts[0][1] === pts[n - 1][1];
  if (!closed) return simplify(pts, tol);
  let far = 1, best = -1;
  for (let i = 1; i < n - 1; i++) {
    const d = Math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]);
    if (d > best) { best = d; far = i; }
  }
  const a = simplify(pts.slice(0, far + 1), tol);
  const b = simplify(pts.slice(far), tol);
  return a.concat(b.slice(1));
}

function simplify(pts, tol) {
  if (pts.length < 3 || tol <= 0) return pts;
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let far = -1, best = tol;
    const [ax, ay] = pts[a], [bx, by] = pts[b];
    const dx = bx - ax, dy = by - ay;
    const den = Math.hypot(dx, dy) || 1;
    for (let i = a + 1; i < b; i++) {
      const [px, py] = pts[i];
      const dist = Math.abs(dy * px - dx * py + bx * ay - by * ax) / den;
      if (dist > best) { best = dist; far = i; }
    }
    if (far > 0) { keep[far] = 1; stack.push([a, far], [far, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}

/**
 * Rings inside a frame, ready to project.
 *   frame  {w, e, s, n} in degrees
 *   tol    simplification tolerance in degrees (default: 1/400th of the width)
 * Returns { land: [[ [lon,lat], … ], … ], borders: [ … ] }
 */
export function outlinesIn(frame, tol) {
  const { w, e, s, n } = frame;
  const t = tol == null ? Math.max(0.0005, (e - w) / 400) : tol;
  const pick = (set) => {
    const out = [];
    for (const d of set) {
      const [x0, y0, x1, y1] = bbox(d);
      if (x1 < w || x0 > e || y1 < s || y0 > n) continue;
      const pts = simplifyRing(decode(d), t);
      if (pts.length >= 2) out.push(pts);
    }
    return out;
  };
  return { land: pick(RAW.land), borders: pick(RAW.borders) };
}
