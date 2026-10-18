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
     i  Edge: a place within policy.edge_km (15) of its region's ring edge, or inside another region's ring and not its own, can
        belong to a NEIGHBOURING region. erasnap.py (which has the place's coordinates) records which regions could claim it
        (snapshot edge_neighbours) and this file keeps the note only in a year when EVERY such neighbour has the SAME regime label
        (rule j); a place the archive's table marks `edge`, or with no neighbour to compare, is in places_silent and never noted.
     j  EDGE AGREEMENT. For a place in edge_neighbours the note needs, for the year, in EACH neighbouring region: exactly one kept era
        that covers the year, does not overlap another, is not approximate or contested (nor unassessed unless the policy allows it),
        has no refused era over the year, and carries the SAME label as the place's own era. Anything unknown (no era, a refused
        era, a different label, a missing region) is silence: whyNot says "edge" (or "ring-conflict" where the place lies in a
        neighbour's ring and not its own). Where every neighbour agrees the note is drawn and says so (edgeAgree, data-era-edge-agree).
        If the year is not a boundary of the own era, a neighbour whose era begins that year must have had the same label just
        before it too (the event could be on either side of that neighbour's change).
   l  BOUNDARY MARGIN. The Atlas marks an era `approx` when its start or end is uncertain (a lower bound, a founding date, sources that
        differ, de facto and de jure changes more than a year apart) and `contested` when its dates or its regime are disputed. That
        uncertainty is about the BOUNDS, not the middle: an event in 1830 in a region that became the Two Sicilies in 1816 and Italy
        in 1861 is under the Two Sicilies whichever of 1815 or 1816 is right. Since contract 1.10.0 every assessed era carries
        fromMargin / toMargin (whole years of uncertainty on its start and end; 0 = the sources agree on one year; null = unknowable),
        contestedScope (none | bounds | regime | part) and marginSourced (false: the margin rests on dates the assessor knew but did
        not find in a fetched page). A note on such an era is allowed only for a year MORE than the reach from EACH numeric bound (the
        start; the end only if the era is closed):
            year - from > max(N, fromMargin)   and   to - year > max(N, toMargin)
        where N is the snapshot's policy.margin_years (default 5; 0 switches the floor off) and, where marginSourced is false, N is
        added again: a softer margin, PROVISIONAL, and counted apart (data-era-margin-unsourced). A null margin on a bound means the
        bound is unknowable, and the builder refuses the era. An approx era from a contract with no margins at all (before 1.10.0)
        gets margin 0 on each side, recorded as margin_src "fallback": only the floor N holds it (PROVISIONAL, not an Atlas fact).
        `contested` is used only where contestedScope is "none" or "bounds" (policy.contested = "scope", the default); "regime" and
        "part" are silent (a part cannot be told from the ring), and so is a contested era with NO scope, unless policy.contested =
        "margin" (the what-if for a contract before 1.10.0). policy.contested = "refuse" refuses every contested era; policy.approx =
        "refuse" refuses every approx era. The snapshot records each decision in the era's margin_ok {kind, first, last} (the first and
        last year a note may use) and the library recomputes it from the margins and N: a record that does not agree is silence
        (whyNot "bad-margin"). Within the reach the reason is "margin". A note on an approx or contested era says so (data-era-approx /
        data-era-contested), and its words are unchanged: the regime label and "per the Record Atlas", no bound of the era in them.
   m  RULERS (off unless the archive asks; the Atlas's contract 1.11.0+, today for one region). A note may name who reigned, beside the
        regime label: "· At the time: Naples / the Two Sicilies (Ferdinand II) per the Record Atlas". rulerAt(snap, region, year) names a
        ruler only when ALL of these hold, else null (whyNoRuler says which fails):
          - the snapshot says the region HAS rulers (rulers[region].has === true: the contract's hasRulers; a missing field is NOT "none",
            it is unknown, and unknown is silence) and every reign row is usable;
          - exactly ONE reign covers the year, a reign covering [fromYear - fromMargin, toYear + toMargin] (to open: no end); two reigns
            that overlap there (Joanna III and Charles IV; a changeover year) are null, never a pick;
          - the year is MORE than max(N, fromMargin) after the reign's start and, if the reign is closed, more than max(N, toMargin)
            before its end (N = policy.margin_years: the same floor as rule l);
          - the reign's polityId is one the era's regime allows (policy.ruler_polities[regime]: a Naples reign in a Two Sicilies era is null);
          - the region's era for that year is the single kept era covering it, with none refused over the year.
        The name shown is the Atlas's `name` exactly (not translated, not normalised); the polity shown is the regime label, never the
        polity string; the note ALWAYS keeps "per the Record Atlas". A boundary-year note ("From that year") and an edge note (a place
        held to its neighbours) name no ruler. eraAt returns the ruler (era.ruler: {name, polityId, from, to, q} or null); the note
        draws it only when the archive asks for it (EraNote rulers), as data-era-ruler and a span.era-ruler.
   Rule c is the PAGE's. Rule i is prepared by the snapshot builder, which has the place's coordinates; this file reads the result.

   THE SNAPSHOT (JSON; version 5)
     version        5
     built          the day it was built, YYYY-MM-DD
     contract       { name, version, generated, sha256 }   the contract the snapshot was cut from (sha256 of the file's bytes)
     atlas          { base: "https://recordatlas.org", rings_source: "contract"|"file"|"none", rings_sha256: <sha of the file>|null }
     policy         { unassessed: "refuse"|"allow", boundary: "newer"|"silent", recent_from: 1990, edge_km: 15, edge: "agree"|"strict",
                      approx: "refuse"|"margin", contested: "refuse"|"scope"|"margin", margin_years: 5, margins: { <era id>: years },
                      ruler_polities: { <regime id>: [ <polityId> ] } }
     regions        { <region id>: [ { id, from, to|null, present, regime, label, polity, basis, seeded_from_archive, approx,
                                       contested, assessed, why, url, from_margin, to_margin, margin_src, contested_scope,
                                       margin_ok } ] }
     places         { <folded place key>: <region id> }   fold() of the place as the archive prints it
     places_silent  { <folded place key>: "edge"|"marked-edge"|"ring-conflict" }   places the builder refused, so they can be counted
     edge_neighbours { <folded place key>: { kind: "edge"|"ring-conflict", regions: [ <region id> ] } }   mapped places that lie near
                    their region's ring edge (or inside another's ring): the regions that could claim them, whose eras the note is
                    held to (rule j)
     unchecked_edge [ <folded place key> ]    mapped places that had no coordinates, so the ring-edge rule could not be applied
     dropped        [ { region, id, from, to, reason } ]   eras the builder refused (so a count of what was left silent can say why)
     quality        { counts: { gaps, overlaps }, gaps: [...], overlaps: [...] }   the contract's own lists, the entries that name
                    a region of this snapshot (the lookup is silent there)
     rulers         { <region id>: { has: true|false|null, why: null|text, reigns: [ { name, polity_id, from, to, from_year, to_year,
                    from_margin, to_margin, margin_why, q, source } ] } }   the contract's rulers (1.11.0+) for the regions the snapshot
                    holds; has is the contract's hasRulers (null: the contract has no such field), true only if every reign row is usable
   No import: this runs in node as it does in a build, so the kit can test it without Astro. */

export const VERSION = 5;
export const SRC_ATLAS = "per the Record Atlas";
export const SRC_OWN = "per this archive's own research";
export const PRE_NORMAL = "· At the time: ";
export const PRE_BOUNDARY = "· From that year: ";
export const RECENT_FROM = 1990;

/* The note's style, drawn ONCE on a page that has at least one note (EraNote.astro: claim(Astro.request, ERA_CSS_KEY)) and nowhere
   else: it was a bundled component style, which every page that merely imported the component carried. Muted and token-driven. */
export const ERA_CSS_KEY = "kit:era-css";
export const ERA_CSS = ".era-note{display:block;margin:.1rem 0 0;font-family:var(--sans,system-ui,sans-serif);font-size:.82rem;line-height:1.35;"
  + "font-weight:400;font-style:normal;letter-spacing:normal;text-transform:none;color:var(--ink-2,#444)}"
  + ".era-note .era-src{white-space:nowrap}"
  + ".era-note a.era-src{color:inherit;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:.15em}"
  + ".era-note a.era-src:hover,.era-note a.era-src:focus-visible{color:var(--accent,var(--ink,#000))}"
  + "@media print{.era-note a.era-src{text-decoration:none}}";

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

/* Rule l. A margin is a whole number of years >= 0. */
const isMargin = (m) => Number.isInteger(m) && m >= 0;
export const MARGIN_KINDS = ["approx", "contested", "both", "margin"];
export const SCOPES = ["none", "bounds", "regime", "part"];
export const MARGIN_YEARS = 5;
/* N, the floor of every margin: the snapshot's policy.margin_years, else 5. */
const floorOf = (pol) => (pol && isMargin(pol.margin_years) ? pol.margin_years : MARGIN_YEARS);

/* How far from a bound a year must be, at the least, for the era to be used: max(N, the Atlas's margin), and N more where the margin is
   not sourced (marginSourced false: the assessor knew the date but did not find it in a fetched page). null: the side has no margin. */
function reach(m, n, soft) {
  return isMargin(m) ? Math.max(n, m) + (soft ? n : 0) : null;
}

/* What the era's own margins allow: the first and last year (inclusive) a note may use, and the kind of reason the era has one.
   null where the era is clean and carries no margin (nothing to record). `last` null: the era is still running (no end bound).
   A year must be MORE than the reach from each numeric bound: year - from > reach, to - year > reach (a reach of 0 is a clean date). */
export function marginSpan(e, n) {
  const ap = flag(e.approx) === "yes", co = flag(e.contested) === "yes";
  const soft = e.margin_sourced === false;
  const rf = reach(e.from_margin, n, soft), rt = e.to === null ? null : reach(e.to_margin, n, soft);
  if (!ap && !co && rf === null && rt === null) return null;
  return { kind: ap && co ? "both" : ap ? "approx" : co ? "contested" : "margin",
           first: e.from + (rf !== null && rf > 0 ? rf + 1 : 0), last: e.to === null ? null : e.to - 1 - (rt !== null ? rt : 0) };
}

/* Is this era usable in this year as far as its flags, scope and margins go? null: yes. Otherwise the reason: "approx" / "contested"
   (the policy or the contract's scope refuses the era), "margin" (the year is within the reach of a bound), "bad-margin" (the snapshot's
   record does not agree with the margins). Pure. */
export function marginGate(e, year, pol) {
  const ap = flag(e.approx), co = flag(e.contested);
  if (ap === "yes" && pol.approx !== "margin") return "approx";
  /* only a scope of "none" or "bounds" is used (the dispute, if any, is about WHEN the change happened); "regime" and "part" are silent
     whatever else is true; no scope at all, on a contested era, only under the explicit what-if policy "margin" */
  if (e.contested_scope === "regime" || e.contested_scope === "part") return "contested";
  if (co === "yes") {
    const cp = pol.contested;
    if (cp !== "scope" && cp !== "margin") return "contested";
    if (e.contested_scope !== "bounds" && e.contested_scope !== "none" && !((e.contested_scope === null || e.contested_scope === undefined) && cp === "margin")) return "contested";
  }
  const n = floorOf(pol);
  const span = marginSpan(e, n);
  if (span === null) return null;
  if ((ap === "yes" || co === "yes") && !(isMargin(e.from_margin) && (e.to === null || isMargin(e.to_margin)))) return ap === "yes" ? "approx" : "contested";
  const r = e.margin_ok;
  if (r == null || typeof r !== "object" || r.kind !== span.kind || r.first !== span.first || r.last !== span.last) return "bad-margin";
  return year >= span.first && (span.last === null || year <= span.last) ? null : "margin";
}

export const VALID_SILENT = ["edge", "marked-edge", "ring-conflict"];
export const EDGE_KINDS = ["edge", "ring-conflict"];

/* Is there an era (kept or refused) of this region that ends in the year `e` begins? Then e.from is a boundary. */
function hasPredecessor(snap, region, eras, e) {
  if (eras.some((o) => o !== e && numeric(o) && o.to === e.from)) return true;
  return (snap.dropped || []).some((d) => dropOk(d) && d.region === region && d.to === e.from);
}

/* Rule j: does the neighbouring region `nb` have, for this year, the same label as the place's own era, and nothing unknown? Pure and
   conservative: every doubt is a no. `mine` is the place's own era, `boundary` whether the note is a boundary-year note. */
function neighbourAgrees(snap, nb, year, mine, boundary, pol) {
  if (typeof nb !== "string" || !own(snap.regions, nb) || !Array.isArray(snap.regions[nb])) return false;
  const eras = snap.regions[nb];
  const dropped = (snap.dropped || []).filter((d) => dropOk(d) && d.region === nb);
  if (dropped.some((d) => covers(d, year))) return false;
  const covering = eras.filter((x) => numeric(x) && covers(x, year));
  if (covering.length !== 1) return false;
  const x = covering[0];
  if (eras.some((o) => o !== x && numeric(o) && meets(x, o))) return false;
  if (marginGate(x, year, pol) !== null) return false;
  if ((flag(x.approx) === "unassessed" || flag(x.contested) === "unassessed") && pol.unassessed !== "allow") return false;
  if (label(x) !== label(mine)) return false;
  if (!boundary && year === x.from) {
    /* the neighbour's era begins this year: the event may be before its change, so what came just before must agree too */
    if (dropped.some((d) => d.to === year)) return false;
    const before = eras.filter((o) => o !== x && numeric(o) && o.to === year);
    if (before.length === 0 || before.some((o) => label(o) !== label(mine) || flag(o.approx) === "yes" || flag(o.contested) === "yes")) return false;
  }
  return true;
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
  if (covering.length > 1 || refused.length > 0 || covering.some((e) => eras.some((o) => o !== e && numeric(o) && meets(e, o)))) return no("contested");
  const e = covering[0];
  const recentFrom = opts && opts.recentFrom !== undefined ? opts.recentFrom : (isYear(pol.recent_from) ? pol.recent_from : RECENT_FROM);
  if (e.to === null && year >= recentFrom) return no("recent");
  let boundary = false;
  if (year === e.from && hasPredecessor(snap, region, eras, e)) {
    if (pol.boundary !== "newer") return no("boundary");
    boundary = true;
  }
  const mg = marginGate(e, year, pol);
  if (mg !== null) return no(mg);
  const unassessed = flag(e.approx) === "unassessed" || flag(e.contested) === "unassessed";
  if (unassessed && pol.unassessed !== "allow") return no("unassessed");
  if (!label(e)) return no("no-label");
  if (e.id !== eraId(region, e.from)) return no("bad-id");
  let edgeAgree = false;
  if (own(snap.edge_neighbours, key)) {
    const en = snap.edge_neighbours[key];
    const kind = en != null && typeof en === "object" && EDGE_KINDS.includes(en.kind) ? en.kind : null;
    const list = en != null && Array.isArray(en.regions) ? en.regions : [];
    if (kind === null || list.length === 0 || list.some((nb) => nb === region || !neighbourAgrees(snap, nb, year, e, boundary, pol))) return no(kind || "edge");
    edgeAgree = true;
  }
  return { why: "ok", region, e, boundary, key, unassessed, edgeAgree };
}

/* Rule m. A reign row the library can read: a name, a polityId slug, whole-number years (the end may be null: the reign goes on) and whole-number
   margins. One unusable row leaves the whole region silent: the row might be the one that overlaps the year. */
const SLUG = /^[a-z0-9][a-z0-9-]*$/;
export const reignOk = (r) => r != null && typeof r === "object" && typeof r.name === "string" && r.name.trim() !== ""
  && typeof r.polity_id === "string" && SLUG.test(r.polity_id) && isYear(r.from_year)
  && (r.to_year === null || (isYear(r.to_year) && r.from_year <= r.to_year))
  && isMargin(r.from_margin) && (r.to_year === null ? (r.to_margin === null || isMargin(r.to_margin)) : isMargin(r.to_margin));

/* Does this reign touch the year, at all, within its own margins? [fromYear - fromMargin, toYear + toMargin]; an open reign has no end. */
const reignTouches = (r, year) => r.from_year - r.from_margin <= year && (r.to_year === null || year <= r.to_year + (r.to_margin || 0));

export const RULER_WHY = ["snapshot", "year", "no-region", "no-rulers", "bad-rows", "no-era", "no-reign", "overlap", "polity", "margin", "ok"];

/* Why a region and a year name no ruler, or "ok" with the reign. Pure. The order is the order a person would ask the questions in. */
function rulerDecide(snap, region, year) {
  const no = (why) => ({ why });
  if (!snap || typeof snap !== "object" || snap.version !== VERSION) return no("snapshot");
  if (!isYear(year)) return no("year");
  if (typeof region !== "string" || !own(snap.regions, region) || !Array.isArray(snap.regions[region])) return no("no-region");
  const rs = own(snap.rulers, region) ? snap.rulers[region] : null;
  if (rs == null || typeof rs !== "object" || rs.has !== true || !Array.isArray(rs.reigns) || rs.reigns.length === 0) return no("no-rulers");
  if (!rs.reigns.every(reignOk)) return no("bad-rows");
  const eras = snap.regions[region];
  const pol = snap.policy && typeof snap.policy === "object" ? snap.policy : {};
  const covering = eras.filter((e) => numeric(e) && covers(e, year));
  const refused = (snap.dropped || []).filter((d) => dropOk(d) && d.region === region && covers(d, year));
  if (covering.length !== 1 || refused.length > 0) return no("no-era");
  const touching = rs.reigns.filter((r) => reignTouches(r, year));
  if (touching.length === 0) return no("no-reign");
  if (touching.length > 1) return no("overlap");
  const r = touching[0];
  const allowed = own(pol.ruler_polities, covering[0].regime) ? pol.ruler_polities[covering[0].regime] : null;
  if (!Array.isArray(allowed) || !allowed.includes(r.polity_id)) return no("polity");
  const n = floorOf(pol);
  if (!(year - r.from_year > Math.max(n, r.from_margin)) || (r.to_year !== null && !(r.to_year - year > Math.max(n, r.to_margin)))) return no("margin");
  return { why: "ok", reign: r };
}

/* Why no ruler for this region and year (one of RULER_WHY), or "ok". An archive that reports "n notes, k with a ruler, the rest silent because ..." uses it. */
export function whyNoRuler(snap, region, year) {
  return rulerDecide(snap, region, year).why;
}

/* Who reigned in this region in this year, as the Atlas states it, or null. -> { name, polityId, from, to, fromYear, toYear, q }.
   `name` is the Atlas's own field, not translated or normalised; from / to are the dates as the source states them (to null: still reigning). */
export function rulerAt(snap, region, year) {
  const d = rulerDecide(snap, region, year);
  if (d.why !== "ok") return null;
  const r = d.reign;
  return { name: r.name, polityId: r.polity_id, from: r.from === undefined ? null : r.from, to: r.to === undefined ? null : r.to, fromYear: r.from_year, toYear: r.to_year, q: typeof r.q === "string" ? r.q : null };
}

/* The era a note may name for this place in this year, or null. The year must already be a plain one (plainYear).
   -> { region, place, id, label, from, to, year, source, seeded, href, boundary, unchecked, unassessed, assessed, approx, contested, edgeAgree, basis, ruler } */
export function eraAt(snap, place, year, opts) {
  const d = decide(snap, place, year, opts);
  if (d.why !== "ok") return null;
  const { region, e } = d;
  const seeded = e.seeded_from_archive === true;
  return {
    region, place: d.key, id: e.id, label: label(e), from: e.from, to: e.to, year,
    source: seeded ? SRC_OWN : SRC_ATLAS, seeded, href: eraHref(snap, region, e),
    boundary: d.boundary, unchecked: Array.isArray(snap.unchecked_edge) && snap.unchecked_edge.includes(d.key),
    unassessed: d.unassessed, assessed: !d.unassessed, approx: flag(e.approx) === "yes", contested: flag(e.contested) === "yes", unsourced: e.margin_sourced === false && marginSpan(e, floorOf(snap.policy)) !== null, edgeAgree: d.edgeAgree, basis: typeof e.basis === "string" ? e.basis : null,
    /* rule m: no ruler on a boundary-year note ("From that year") or on an edge note (held to its neighbours) */
    ruler: d.boundary || d.edgeAgree ? null : rulerAt(snap, region, year),
  };
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* The markup of one note, as components/EraNote.astro draws it (the node test holds the component to these attributes).
   opts.rulers === true draws the ruler too (rule m): the archive's choice, off by default. */
export function renderEra(era, opts) {
  if (!era) return "";
  const src = era.href
    ? `<a class="era-src" href="${esc(era.href)}" rel="noopener">${esc(era.source)}</a>`
    : `<span class="era-src">${esc(era.source)}</span>`;
  const b = era.boundary === true;
  const ru = opts && opts.rulers === true && era.ruler && typeof era.ruler.name === "string" && era.ruler.name !== "" ? era.ruler : null;
  return `<span class="era-note" data-era="${esc(era.id)}" data-era-year="${esc(era.year)}"${b ? ' data-era-boundary="1"' : ""}`
    + ` data-era-assessed="${era.assessed === true ? "1" : "0"}"${era.approx === true ? ' data-era-approx="1"' : ""}${era.contested === true ? ' data-era-contested="1"' : ""}${era.unsourced === true ? ' data-era-margin-unsourced="1"' : ""}${era.edgeAgree === true ? ' data-era-edge-agree="1"' : ""}`
    + `${typeof era.place === "string" && era.place !== "" ? ` data-era-place="${esc(era.place)}"` : ""}${ru ? ` data-era-ruler="${esc(ru.name)}"` : ""}>`
    + `<span class="era-pre">${b ? PRE_BOUNDARY : PRE_NORMAL}</span><span class="era-lab">${esc(era.label)}</span>${ru ? ` <span class="era-ruler">(${esc(ru.name)})</span>` : ""} ${src}</span>`;
}
