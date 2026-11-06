/* WHERE WE HAVE LOOKED (PERSON-PAGE-SPEC.md 2a, `#looked`): the searches an archive has made for a person's SURNAME at THEIR PLACES, what each gave
   back, and which volumes the Record Atlas lists for those places that nobody has opened for the name yet.

   This file is the whole logic: grouping, progress, wording, and the one rule that matters. The component only draws what it returns. No archive's
   words are in here: the archive hands over rows in a normalised shape and, if its outcome words differ from the default five, a table of them.

   THE RULE: «we looked and found nothing» and «we have not looked» must never read alike, and a nothing is only claimed where every spelling of the name
   was tried.
     - an outcome class is one of  found · partial · nil · blocked · notyet.  `nil` is a search that was made and returned nothing; `blocked` and `notyet`
       are searches that were NOT made (a wall, or known and not yet got). They are drawn as «not looked», not as an empty result.
     - a `nil` row is drawn as «looked, nothing found» ONLY when its verdict says every spelling of the name was covered (row.nil.status === "covered", the
       archive having asked the Record Atlas catalogue: surname_variants.py cover). A nil whose verdict says a spelling was not tried is drawn as «looked,
       but not under every spelling» and NAMES the spelling; one whose verdict is missing or "unknown" says the spellings typed are not recorded on the row.
       Neither is ever drawn as an absence. Typography (case, spaces, hyphens, apostrophes) is never a spelling; the archive's verdict already ignores it.
     - a match is by TAG (the surname family and the place), not by person, and the section says so unless every row is the person's own (row.own).

   INPUT  rows     [{ id, src, volume, years, span:[from,to], what, when, outcome, surnames[], places[], href, volumes[], nil, own }]
                   surnames/places are the keys the archive matched this person on (informational); `volumes` are ids of Atlas volumes (places[].volumes[].id)
                   the row read; `nil` is { status: "covered"|"missed"|"unknown", missed: [spellings] } for the PERSON's surname (only for outcome class nil).
          places   [{ key, name, volumes: [{ id, t, u, f, to }], held: { books, checked, bad }|null, atlas: true|false }]   in the order the person lived there
          names    the surname(s) as the page should say them
          span     [from, to] the years the person lived (optional); unopened volumes entirely outside it are counted, not listed
          outcomes { word: { label, cls } }  the archive's own vocabulary (default: DEFAULT_OUTCOMES)
          cap      show at most this many rows per place in full (0 = all); the rest are counted by outcome
   OUTPUT  a model the component draws: { names, byTag, groups[], counts, progress[], noAtlas[] } */

export const CLASS_ORDER = ["found", "partial", "nil", "nilx", "blocked", "notyet"];
export const CLASS_LABEL = {
  found: "Found something", partial: "Read in part", nil: "Looked, nothing found",
  nilx: "Looked, but not under every spelling", blocked: "Could not look", notyet: "Not looked yet",
};
/* the archive's five (yield / partial / nothing / blocked / pending); another archive passes its own */
export const DEFAULT_OUTCOMES = {
  yield: { label: "Yielded", cls: "found" }, partial: { label: "Partly", cls: "partial" }, nothing: { label: "Nothing", cls: "nil" },
  blocked: { label: "Blocked", cls: "blocked" }, pending: { label: "Not yet", cls: "notyet" },
};
const CLASSES = new Set(["found", "partial", "nil", "blocked", "notyet"]);
/* a search that was made, for the progress count; blocked and notyet were not */
const MADE = new Set(["found", "partial", "nil", "nilx"]);

export const listJoin = (xs) => xs.length <= 1 ? (xs[0] || "") : xs.length === 2 ? `${xs[0]} and ${xs[1]}` : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;
export const plural = (n, one, many) => `${n} ${n === 1 ? one : many || one + "s"}`;

/* the class a row is DRAWN in: a nil only keeps its class when the verdict says every spelling was covered */
export function drawnClass(row, outcomes = DEFAULT_OUTCOMES) {
  const o = outcomes[row.outcome];
  if (!o || !CLASSES.has(o.cls)) throw new Error(`personlooked: outcome "${row.outcome}" has no class (one of ${[...CLASSES].join(", ")})`);
  if (o.cls !== "nil") return o.cls;
  return row.nil && row.nil.status === "covered" ? "nil" : "nilx";
}

/* what a nil that is not an absence says, in words */
export function nilNote(row) {
  const v = row.nil || { status: "unknown" };
  if (v.status === "covered") return "";
  if (v.status === "missed" && v.missed && v.missed.length) {
    return `Not shown as an absence: ${listJoin(v.missed)} ${v.missed.length === 1 ? "was" : "were"} not tried in this search, and the Record Atlas lists ${v.missed.length === 1 ? "it" : "them"} as a spelling of the name.`;
  }
  return "Not shown as an absence: the spellings typed are not recorded on this row, so it cannot be said that every spelling of the name was tried.";
}

const overlaps = (span, f, t) => {
  if (!span || span.length < 2 || span[0] == null || span[1] == null) return true;
  if (f == null && t == null) return true;
  const a = f == null ? t : f, b = t == null ? f : t;
  return a <= span[1] && b >= span[0];
};
const years = (f, t) => f == null ? "" : t == null || t === f ? String(f) : `${f}–${t}`;

export function lookedModel({ rows = [], places = [], names = [], span = null, outcomes = DEFAULT_OUTCOMES, cap = 0 } = {}) {
  const order = new Map(places.map((p, i) => [p.key, i]));
  /* each row is listed once: under the place of the first Atlas volume it read, else under the first of the person's places it names */
  const volPlace = new Map();
  for (const p of places) for (const v of p.volumes || []) if (!volPlace.has(v.id)) volPlace.set(v.id, p.key);
  const groups = places.map((p) => ({ key: p.key, name: p.name, held: p.held || null, atlas: p.atlas !== false, rows: [], volumes: [], listed: 0, outside: 0 }));
  const byKey = new Map(groups.map((g) => [g.key, g]));
  for (const r of rows) {
    const cls = drawnClass(r, outcomes);
    const label = (outcomes[r.outcome] || {}).label || r.outcome;
    const home = (r.volumes || []).map((id) => volPlace.get(id)).find(Boolean)
      || (r.places || []).filter((k) => order.has(k)).sort((a, b) => order.get(a) - order.get(b))[0];
    const drawn = { ...r, cls, label, nilnote: cls === "nilx" ? nilNote(r) : "" };
    const g = home && byKey.get(home);
    if (!g) throw new Error(`personlooked: row "${r.id || r.src}" names none of this person's places; the archive must hand over only the rows that match`);
    g.rows.push(drawn);
  }
  const rank = (c) => CLASS_ORDER.indexOf(c);
  const counts = { found: 0, partial: 0, nil: 0, nilx: 0, blocked: 0, notyet: 0, rows: 0 };
  for (const g of groups) {
    g.rows.sort((a, b) => rank(a.cls) - rank(b.cls));   // stable: the archive's own order (newest first) holds within a class
    for (const r of g.rows) { counts[r.cls]++; counts.rows++; }
    /* the volumes the Atlas lists for this place, each with what has been done to it for this name */
    const state = new Map();
    for (const r of g.rows) for (const id of r.volumes || []) {
      const s = state.get(id);
      const better = (a, b) => rank(a) < rank(b);
      state.set(id, !s || better(r.cls, s) ? r.cls : s);
    }
    const vols = (places.find((p) => p.key === g.key).volumes || []).map((v) => {
      const st = state.get(v.id) || null;
      return { ...v, state: st, years: years(v.f, v.to), inSpan: overlaps(span, v.f, v.to), made: !!st && MADE.has(st) };
    });
    g.looked = vols.filter((v) => v.made);
    g.inPart = g.looked.filter((v) => v.state === "partial").length;
    const open = vols.filter((v) => !v.made);
    g.unopened = open.filter((v) => v.inSpan);
    g.outside = open.length - g.unopened.length;
    g.total = vols.length;
    g.shown = cap > 0 && g.rows.length > cap ? g.rows.slice(0, cap) : g.rows;
    g.hidden = g.rows.slice(g.shown.length);
    g.hiddenBy = {};
    for (const r of g.hidden) g.hiddenBy[r.cls] = (g.hiddenBy[r.cls] || 0) + 1;
  }
  const progress = groups.filter((g) => g.total > 0).map((g) => {
    const n = g.looked.length, name = listJoin(names) || "this name";
    const part = g.inPart ? ` (${g.inPart === n ? (n === 1 ? "only in part" : "all only in part") : `${g.inPart} only in part`})` : "";
    return `${g.name}: the Record Atlas lists ${plural(g.total, "volume")}; ${n === 0 ? "none has" : n === 1 ? "1 has" : `${n} have`} been looked at for ${name}${part}.`;
  });
  /* a place the archive's own register names but the Atlas has no volume for: said, not left silent */
  const noAtlas = groups.filter((g) => g.total === 0).map((g) => g.name);
  const byTag = rows.some((r) => !r.own);
  return { names, byTag, groups, counts, progress, noAtlas, span };
}
