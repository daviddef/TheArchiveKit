/* The pure half of components/EraNote.astro: who held a piece of ground in a given year, worked out from a SNAPSHOT of the Record
   Atlas's versioned CONTEXT CONTRACT (context.json) that the archive keeps in its own repository (kit/tools/erasnap.py builds it).

   WHAT THIS IS FOR. A quiet "at the time" note beside a dated place-event: "Briatico, 1860 · Naples / the Two Sicilies, per the
   Record Atlas". It is CONTEXT about the ground, never a claim about the family, and it says where it came from. It is a
   SILENCE-FIRST function: it answers only when every rule below holds, and otherwise returns null, because a missing note costs
   a reader nothing and a wrong one costs the archive its word.

   THE RULES (kit/docs/era-notes.md has the evidence for each)
     a  Only the Atlas's REGION eras are used (`regions` in the contract), mapped from the place by a table the ARCHIVE supplies.
        Never the contract's `countries` layer: it is keyed on flag pages, most of its eras are unreviewed, and a sub-national
        place needs the sub-national answer (Vodnjan in 1925 is not the Kingdom of Serbs, Croats and Slovenes).
     b  The interval is HALF-OPEN, as the contract states it: an era covers from <= year < to. `to` null is the era still running
        (present). An era needs a whole-number `from`, a whole-number `to` or null, and a display label.
        The label is the contract's regimeLabel (never the era's free-text `polity`, which can name today's province), except for
        the few regimes that are a bare shorthand ("Napoleonic"), which erasnap.py shows only with the era's own polity.
     c  Never on a living, held-out or noindex page: the PAGE's rule (this function cannot know who is living); checkera.py fails
        the build if a note is found on such a page.
     d  A year ON a boundary: the contract says a year equal to a boundary belongs to the NEWER era, and the snapshot records that
        the contract said so (policy.boundary = "newer"). A year-only date cannot say which side of the change it is on, so such a
        note does not claim the older or the newer ground "at the time": it is drawn "From that year: <the newer label>", which is
        true whichever side of the change the event fell. If the snapshot does not say "newer", a boundary year is silent. A date
        the page marks uncertain ("c. 1783", "before 1820") has no year at all (plainYear gives null).
     e  The note links to the ERA the contract names (its `url`, on the Atlas's base), and carries the contract's era id in data-era.
     f  Where the contract's `basis` says an era's bands were seeded from this estate's own research (seeded:...) the snapshot says
        so (`seeded_from_archive`) and the note says "per this archive's own research": the Atlas is then the archive quoting itself.
     g  null is not false. `contested` and `approx` null mean nobody has assessed the era; they are UNCERTAIN, and silent, unless the
        snapshot says policy.unassessed = "allow" (a deliberate, recorded choice an archive makes with erasnap.py --unassessed).
     h  THE QUIET RULE: an event in the era that is still running (`to` null) from policy.recent_from (default 1990) is silent: a
        modern event teaches nothing. Override: opts.recentFrom (a number; Infinity switches it off) or erasnap.py --recent-from.
     i  Edge: a place within policy.edge_km (15) of its region's ring edge, or one the archive's table marks `edge`, was removed
        from the snapshot's places by erasnap.py and is recorded in places_silent; whyNot says "edge" / "marked-edge".
   Rule c is the PAGE's. Rule i is done by the snapshot builder, which has the place's coordinates; this file only reads the result.

   THE SNAPSHOT (JSON; version 2)
     version        2
     built          the day it was built, YYYY-MM-DD
     contract       { name, version, generated, sha256 }   the contract the snapshot was cut from (sha256 of the file's bytes)
     atlas          { base: "https://recordatlas.org", rings_sha256 }
     policy         { unassessed: "refuse"|"allow", boundary: "newer"|"silent", recent_from: 1990, edge_km: 15 }
     regions        { <region id>: [ { id, from, to|null, present, regime, label, polity, basis, seeded_from_archive, approx,
                                       contested, url } ] }
     places         { <folded place key>: <region id> }   fold() of the place as the archive prints it
     places_silent  { <folded place key>: "edge"|"marked-edge"|"ring-conflict" }   places the builder refused, so they can be counted
     unchecked_edge [ <folded place key> ]    mapped places that had no coordinates, so the ring-edge rule could not be applied
     dropped        [ { region, id, from, to, reason } ]   eras the builder refused (so a count of what was left silent can say why)
     quality        { counts: { gaps, overlaps }, gaps: [...], overlaps: [...] }   the contract's own lists, the entries that name
                    a region of this snapshot (the lookup is silent there)
   No import: this runs in node as it does in a build, so the kit can test it without Astro. */

export const VERSION = 2;
export const SRC_ATLAS = "per the Record Atlas";
export const SRC_OWN = "per this archive's own research";
export const PRE_NORMAL = "· At the time: ";
export const PRE_BOUNDARY = "· From that year: ";
export const RECENT_FROM = 1990;

const own = (o, k) => o != null && typeof o === "object" && Object.prototype.hasOwnProperty.call(o, k);

/* A place as it is compared: case, accents and apostrophes gone, every other run of punctuation and spaces one space. The
   archive's table is keyed on this, and erasnap.py folds the same way (the shared cases hold the two together). */
export function fold(s) {
  return String(s == null ? "" : s)
    .normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/['’`]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

const MONTHS = "(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)";
const PLAIN = new RegExp(`^(?:(?:\\d{1,2}\\s+)?${MONTHS}\\.?\\s+)?(\\d{4})$`, "i");
const ISO = /^(\d{4})(?:-\d{2}(?:-\d{2})?)?$/;

/* The year of an event, but only where the page's own date is a plain one: "1860", "March 1860", "12 March 1860", "1860-03-12".
   `date` is the text the page prints, `year` the number the archive holds. They must agree; anything the page marks as
   uncertain ("c. 1860", "about 1860", "before 1860", "1860?") or cannot be read as a single year gives null. */
export function plainYear(date, year) {
  if (!Number.isInteger(year) || year < 1 || year > 9999) return null;
  if (typeof date !== "string") return null;
  const s = date.trim().replace(/\s+/g, " ");
  const m = PLAIN.exec(s) || ISO.exec(s);
  if (!m || Number(m[1]) !== year) return null;
  return year;
}

/* The id a region era has in the contract, and so in data-era: <region>--era-<from>. */
export const eraId = (region, from) => `${region}--era-${from}`;

const isYear = (n) => Number.isInteger(n) && n >= 1 && n <= 9999;
const baseOf = (snap) => {
  const b = snap && snap.atlas && typeof snap.atlas.base === "string" ? snap.atlas.base.replace(/\/+$/, "") : "";
  return /^https:\/\/[^/?#\s]+$/i.test(b) ? b : null;
};

/* The Atlas page for a region, or null where the snapshot names no base. */
export function regionHref(snap, region) {
  const b = baseOf(snap);
  return b && /^[a-z0-9][a-z0-9-]*$/.test(String(region)) ? `${b}/region/${region}/` : null;
}

/* The link to the ERA, which is what the contract asks a citation to carry: the contract's own `url` (a path on the Atlas's base),
   accepted only if it is the path the id implies, /region/<region>/#era-<from>. */
export function eraHref(snap, region, e) {
  const b = baseOf(snap);
  if (!b || !e || typeof e.url !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(String(region))) return null;
  return e.url === `/region/${region}/#era-${e.from}` ? b + e.url : null;
}

const label = (e) => (typeof e.label === "string" ? e.label.trim() : "");
const dropOk = (d) => d != null && typeof d === "object" && isYear(d.from) && (d.to === null || (isYear(d.to) && d.from < d.to));
/* an era with a whole-number start and either a later whole-number end or null (still running) */
export const numeric = (e) => e != null && typeof e === "object" && isYear(e.from) && (e.to === null || (isYear(e.to) && e.from < e.to));
/* from <= year < to; to null runs on */
export const covers = (e, year) => e.from <= year && (e.to === null || year < e.to);
/* do two eras share any year? */
const meets = (a, b) => a.from < (b.to === null ? Infinity : b.to) && b.from < (a.to === null ? Infinity : a.to);
/* "yes", "no" or "unassessed" for a flag the contract carries as true, false or null */
const flag = (v) => (v === true ? "yes" : v === false ? "no" : v === null || v === undefined ? "unassessed" : "yes");

export const VALID_SILENT = ["edge", "marked-edge", "ring-conflict"];

/* Is there an era (kept or refused) of this region that ends in the year `e` begins? Then e.from is a boundary. */
function hasPredecessor(snap, region, eras, e) {
  if (eras.some((o) => o !== e && numeric(o) && o.to === e.from)) return true;
  return (snap.dropped || []).some((d) => dropOk(d) && d.region === region && d.to === e.from);
}

/* Why a place and a year give no note, or "ok" when they give one. The first reason that applies wins; the order is the order
   a person would ask the questions in. Used by eraAt, and by an archive that wants to COUNT what it left silent.
   opts.recentFrom overrides the snapshot's quiet-rule year (Infinity: off). */
export function whyNot(snap, place, year, opts) {
  return decide(snap, place, year, opts).why;
}

function decide(snap, place, year, opts) {
  const no = (why) => ({ why });
  if (!snap || typeof snap !== "object" || snap.version !== VERSION) return no("snapshot");
  if (!isYear(year)) return no("year");
  if (typeof place !== "string" || !fold(place)) return no("place");
  const key = fold(place);
  if (own(snap.places_silent, key) && VALID_SILENT.includes(snap.places_silent[key])) return no(snap.places_silent[key]);
  if (!own(snap.places, key)) return no("no-region");
  const region = snap.places[key];
  if (typeof region !== "string" || !own(snap.regions, region) || !Array.isArray(snap.regions[region])) return no("no-region");
  const eras = snap.regions[region];
  const pol = snap.policy && typeof snap.policy === "object" ? snap.policy : {};
  const refused = (snap.dropped || []).filter((d) => dropOk(d) && d.region === region && covers(d, year));
  const covering = eras.filter((e) => numeric(e) && covers(e, year));
  if (covering.length === 0) return no(refused.length ? "era-refused" : "no-era");
  /* more than one era (kept or refused) at once, or an era that meets another anywhere: a contested stretch */
  if (covering.length > 1 || refused.length > 0 || covering.some((e) => e.contested === true || eras.some((o) => o !== e && numeric(o) && meets(e, o)))) return no("contested");
  const e = covering[0];
  const recentFrom = opts && opts.recentFrom !== undefined ? opts.recentFrom : (isYear(pol.recent_from) ? pol.recent_from : RECENT_FROM);
  if (e.to === null && year >= recentFrom) return no("recent");
  let boundary = false;
  if (year === e.from && hasPredecessor(snap, region, eras, e)) {
    if (pol.boundary !== "newer") return no("boundary");
    boundary = true;
  }
  if (flag(e.approx) === "yes") return no("approx");
  if (flag(e.contested) === "yes") return no("contested");
  const unassessed = flag(e.approx) === "unassessed" || flag(e.contested) === "unassessed";
  if (unassessed && pol.unassessed !== "allow") return no("unassessed");
  if (!label(e)) return no("no-label");
  if (e.id !== eraId(region, e.from)) return no("bad-id");
  return { why: "ok", region, e, boundary, key, unassessed };
}

/* The era a note may name for this place in this year, or null. The year must already be a plain one (plainYear).
   -> { region, id, label, from, to, year, source, seeded, href, boundary, unchecked, unassessed, basis } */
export function eraAt(snap, place, year, opts) {
  const d = decide(snap, place, year, opts);
  if (d.why !== "ok") return null;
  const { region, e } = d;
  const seeded = e.seeded_from_archive === true;
  return {
    region, id: e.id, label: label(e), from: e.from, to: e.to, year,
    source: seeded ? SRC_OWN : SRC_ATLAS, seeded, href: eraHref(snap, region, e),
    boundary: d.boundary, unchecked: Array.isArray(snap.unchecked_edge) && snap.unchecked_edge.includes(d.key),
    unassessed: d.unassessed, basis: typeof e.basis === "string" ? e.basis : null,
  };
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* The markup of one note, as components/EraNote.astro draws it (the node test holds the component to these attributes). */
export function renderEra(era) {
  if (!era) return "";
  const src = era.href
    ? `<a class="era-src" href="${esc(era.href)}" rel="noopener">${esc(era.source)}</a>`
    : `<span class="era-src">${esc(era.source)}</span>`;
  const b = era.boundary === true;
  return `<span class="era-note" data-era="${esc(era.id)}" data-era-year="${esc(era.year)}"${b ? ' data-era-boundary="1"' : ""}>`
    + `<span class="era-pre">${b ? PRE_BOUNDARY : PRE_NORMAL}</span><span class="era-lab">${esc(era.label)}</span> ${src}</span>`;
}
