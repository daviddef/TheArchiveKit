/* An archive's ancestry → the shape AncChart draws.

   The seven archives record their lines two different ways, and neither of
   them is the nested shape the chart wants. So: two readers, one node
   builder, and the rules that matter — what the living may show, and how a
   branch is allowed to end — written once and applied to both.

     ahnen(rows, opts)    a flat ahnentafel: you are 1, your father 2n
     lineage(root, opts)  rows that point at their own parents

   Two archives keep their line as a flat list numbered the old way: you are 1,
   your father is 2, your mother 3, and the father of n is always 2n. That is
   already a tree; it is only written down as a list. This turns it back into
   one, so an archive that has the list gets the drawing without writing a
   second copy of its own ancestry.

   Field names differ between archives (born/byear, bornPlace/birthPlace), so
   every reader is overridable — but the defaults cover what the archives
   actually have, and an archive whose data fits needs to pass nothing.

   The living are named and nothing more. That is the estate's rule, and it is
   enforced here rather than trusted to each caller: a row marked living loses
   its dates and its birthplace on the way through, whatever the file says. */

const yr = (v) => { const m = /\b(\d{4})\b/.exec(String(v ?? "")); return m ? m[1] : ""; };

/* GEDCOM exports shout: "ST. MARY'S, LIMERICK". Quiet an all-caps segment
   down without touching one that was typed properly. */
const quiet = (s) => String(s ?? "").split(/\s*,\s*/)
  .map(part => /[A-Z]/.test(part) && part === part.toUpperCase()
    ? part.toLowerCase().replace(/(^|[\s'-])([a-z])/g, (m, a, b) => a + b.toUpperCase())
    : part)
  .join(", ");

export const dates = (b, d) =>
  b && d ? `${b}–${d}` : b ? `b. ${b}` : d ? `d. ${d}` : "";

/* Every reader an archive may override, and the two rules it may not. */
function readers(opts) {
  const {
    name    = (r) => r.name,
    born    = (r) => yr(r.born ?? r.byear),
    died    = (r) => yr(r.died ?? r.dyear),
    place   = (r) => quiet(r.bornPlace || r.birthPlace || r.place || ""),
    living  = (r) => !!r.living || r.name === "—" || !r.name,
    conf    = (r) => (living(r) ? "living" : (r.sources && r.sources.length) ? "doc" : "lore"),
    extra   = () => ({}),
  } = opts;

  /* The one thing a caller cannot opt out of: a row marked living loses its
     dates and its birthplace here, whatever the file says. Named, and nothing
     more. Enforcing it in one place beats trusting seven callers. */
  return (r) => {
    const isLiving = living(r);
    return {
      n: name(r) || "—",
      d: isLiving ? "" : dates(born(r), died(r)),
      place: isLiving ? "" : place(r),
      conf: conf(r),
      ...extra(r),
    };
  };
}

export function ahnen(rows, opts = {}) {
  const {
    wall   = defaultWall,
    maxGen = 99,
    /* Where to start drawing. An archive whose first two generations are
       living people has three boxes reading "—" before anything is said;
       starting at the first ancestor it can actually name is not hiding
       anything, it is beginning where the archive begins. */
    from   = 1,
  } = opts;
  const box = readers(opts);

  const by = new Map();
  for (const r of rows) if (r.ahn) by.set(Number(r.ahn), r);
  const root0 = Math.floor(Math.log2(from));

  const node = (n) => {
    const r = by.get(n);
    if (!r) return null;
    const b = box(r);
    const gen = Math.floor(Math.log2(n)) - root0;
    if (gen < maxGen) {
      b.f = node(n * 2);
      b.m = node(n * 2 + 1);
    }
    if (!b.f && !b.m && gen > 0) {
      /* Two different silences, and a chart that draws them alike tells a
         lie. A branch can stop because the archive does not know who comes
         next — that is a wall, and it is the interesting kind. Or it can
         stop because this drawing was cut to a readable depth while the data
         runs on — that is not a wall, it is a door, and it should say how
         much is behind it. */
      const deeper = depth(n);
      if (deeper) {
        b.f = { wall: true, kind: "candidate",
                label: `${deeper} more generation${deeper > 1 ? "s" : ""}`,
                note: `The chart stops here to stay readable. Above **${b.n}** this `
                    + `branch is recorded ${deeper} generation${deeper > 1 ? "s" : ""} further back.` };
      } else {
        const w = wall(r, b);
        if (w) b.f = w;
      }
    }
    return b;
  };

  /* How many generations of real rows sit above a slot the drawing cut off.
     Ahnentafel numbers are a binary path — m descends from n exactly when n
     is m's leading bits — so this is a prefix test over the rows, not a
     search of the space below n. It has to be: the deepest slot in one of
     these files is ahn 8,416,259. */
  const bits = (x) => 32 - Math.clz32(x);
  function depth(n) {
    const bn = bits(n);
    let found = 0;
    for (const m of by.keys()) {
      const d = bits(m) - bn;
      if (d > found && Math.floor(m / 2 ** d) === n) found = d;
    }
    return found;
  }

  return node(from);
}

/* The other way an archive writes its ancestry: rows that point at their own
   parents, by id or by slug or by an inline scrap of a person who is not in
   the file at all. Every archive spells that link differently, so the caller
   supplies one function — parentsOf(row) → { f, m } — and gets back the same
   nested shape, under the same rules about the living and about walls.

   Returning a row that is not in the file is allowed and is the point: a
   parent known only as a name on a register is still a real thing the chart
   should draw, and refusing it would quietly shorten the line. */
export function lineage(root, opts = {}) {
  const {
    parentsOf,
    wall   = defaultWall,
    maxGen = 99,
  } = opts;
  if (typeof parentsOf !== "function")
    throw new Error("lineage(): parentsOf(row) is required");
  const box = readers(opts);

  /* A tree that points at its own parents can point in a circle — a bad merge
     is all it takes — and a walk that trusts it will not come back. */
  const walking = new Set();

  const node = (r, gen) => {
    if (!r || walking.has(r)) return null;
    const b = box(r);
    if (gen < maxGen) {
      walking.add(r);
      const { f, m } = parentsOf(r) || {};
      b.f = node(f, gen + 1);
      b.m = node(m, gen + 1);
      walking.delete(r);
    }
    if (!b.f && !b.m && gen > 0) { const w = wall(r, b); if (w) b.f = w; }
    return b;
  };

  return node(root, 0);
}

function defaultWall(r, b) {
  const where = b.place ? b.place.split(/\s*,\s*/)[0] : "";
  const when = /\b(\d{4})\b/.exec(b.d);
  return {
    wall: true,
    kind: "unworked",
    label: where && when ? `Before ${where}, ${when[1]}`
         : where ? `Before ${where}`
         : "No parents recorded",
    note: `No parents are recorded for **${b.n}** in this archive. `
        + (where ? `The line is known back to ${where} and no further.`
                 : `Where the line goes next is not yet known.`),
  };
}
