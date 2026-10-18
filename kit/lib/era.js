/* The pure half of components/EraNote.astro: who held a piece of ground in a given year, worked out from a SNAPSHOT of the Record
   Atlas's sub-national regions that the archive keeps in its own repository (kit/tools/erasnap.py builds it).

   WHAT THIS IS FOR. A quiet "at the time" note beside a dated place-event: "Briatico, 1860 · Naples / the Two Sicilies, per the
   Record Atlas". It is CONTEXT about the ground, never a claim about the family, and it says where it came from. It is a
   SILENCE-FIRST function: it answers only when every rule below holds, and otherwise returns null, because a missing note costs
   a reader nothing and a wrong one costs the archive its word.

   THE RULES (the study of 18 October 2026, kit/docs/era-notes.md, has the evidence for each)
     a  Only the Atlas's REGION eras are used (regions.json), mapped from the place by a table the ARCHIVE supplies. Never a
        country-level lookup: the Atlas's country timelines are keyed on modern countries and are wrong for sub-national
        places (Vodnjan in 1925 is not the Kingdom of Serbs, Croats and Slovenes; Briatico in 1860 is not Sardinia).
     b  A note needs a place that maps to a region AND a year inside exactly one era of that region with a whole-number start and
        end year, not marked approximate, not contested (no other era of the region overlaps it), and with a regime label that
        is a non-empty string. The label is the REGIME's label, never the era's free-text `polity` string (which can name
        today's province, "Italy - Provincia di Vibo Valentia" for a town that is in Reggio).
     d  A year ON an era boundary (equal to the era's from or to) gets no note: a year-only date cannot say which side it is on.
        A date the page marks uncertain ("c. 1783", "about 1772", "before 1820", "after ...", "between ...") has no year here at
        all (plainYear returns null).
     e  The note links to the Atlas's page for the REGION (/region/<id>/): there is no stable deep link to a region era.
     f  Where the Atlas seeded a region's regimes from this estate's own research (the Defranceschi sovereignty bands for Istria,
        Kvarner, Dalmatia, Carnia) the snapshot says so (`seeded_from_archive`) and the note says "per this archive's own
        research", because the Atlas is then the archive quoting itself.
   Rule c (no note on a living, held-out or noindex page) is the PAGE's: this function does not know who is living, so the
   template must not call it for them, and checkera.py fails the build if a note is found on such a page.

   THE SNAPSHOT (JSON; version 1)
     version        1
     built          the day it was built, YYYY-MM-DD
     atlas_commit_or_etag  the Atlas commit (or the file's ETag) the snapshot was cut from
     atlas          { base: "https://recordatlas.org", file_sha256: <of the regions.json it was cut from> }
     regimes        { <regime id>: <label> }   only the regimes the kept eras use
     regions        { <region id>: [ { from, to, regime, approx, contested, seeded_from_archive, sources } ] }
     places         { <folded place key>: <region id> }   fold() of the place as the archive prints it
     dropped        [ { region, from, to, reason } ]       eras the builder refused (informational)
   No import: this runs in node as it does in a build, so the kit can test it without Astro. */

export const VERSION = 1;
export const SRC_ATLAS = "per the Record Atlas";
export const SRC_OWN = "per this archive's own research";

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

/* The id the note carries in data-era, and the gate reads back. */
export const eraId = (region, from) => `${region}--${from}`;

/* The Atlas page for a region, or null where the snapshot names no base. */
export function regionHref(snap, region) {
  const b = snap && snap.atlas && typeof snap.atlas.base === "string" ? snap.atlas.base.replace(/\/+$/, "") : "";
  return /^https:\/\/[^/?#\s]+$/i.test(b) && /^[a-z0-9][a-z0-9-]*$/.test(String(region)) ? `${b}/region/${region}/` : null;
}

const isYear = (n) => Number.isInteger(n) && n >= 1 && n <= 9999;
const label = (snap, e) => {
  if (!own(snap.regimes, e.regime)) return "";
  const l = snap.regimes[e.regime];
  return typeof l === "string" ? l.trim() : "";
};
const numeric = (e) => e != null && typeof e === "object" && isYear(e.from) && isYear(e.to) && e.from < e.to;

/* Why a place and a year give no note, or "ok" when they give one. The first reason that applies wins; the order is the order
   a person would ask the questions in. Used by eraAt, and by an archive that wants to COUNT what it left silent. */
export function whyNot(snap, place, year) {
  if (!snap || typeof snap !== "object" || snap.version !== VERSION) return "snapshot";
  if (!isYear(year)) return "year";
  if (typeof place !== "string" || !fold(place)) return "place";
  const key = fold(place);
  if (!own(snap.places, key)) return "no-region";
  const region = snap.places[key];
  if (typeof region !== "string" || !own(snap.regions, region) || !Array.isArray(snap.regions[region])) return "no-region";
  const eras = snap.regions[region];
  /* every era that touches this year, edges included: more than one is a contested stretch or a boundary */
  const touching = eras.filter((e) => numeric(e) && e.from <= year && year <= e.to);
  if (touching.length === 0) {
    const refused = (snap.dropped || []).some((d) => d && d.region === region && isYear(d.from) && isYear(d.to) && d.from <= year && year <= d.to);
    return refused ? "era-refused" : "no-era";
  }
  const overlapped = (e) => eras.some((o) => o !== e && numeric(o) && o.from < e.to && e.from < o.to);
  const inside = touching.filter((e) => e.from < year && year < e.to);
  if (inside.length > 1 || touching.some((e) => e.contested === true || overlapped(e))) return "contested";
  if (inside.length === 0) return "boundary";
  const e = inside[0];
  if (e.approx !== false && e.approx !== undefined) return "approx";
  if (e.contested !== false && e.contested !== undefined) return "contested";
  if (!label(snap, e)) return "no-label";
  return "ok";
}

/* The era a note may name for this place in this year, or null. The year must already be a plain one (plainYear).
   -> { region, id, label, from, to, year, source, seeded, href } */
export function eraAt(snap, place, year) {
  if (whyNot(snap, place, year) !== "ok") return null;
  const region = snap.places[fold(place)];
  const e = snap.regions[region].find((x) => numeric(x) && x.from < year && year < x.to);
  const seeded = e.seeded_from_archive === true;
  return {
    region, id: eraId(region, e.from), label: label(snap, e), from: e.from, to: e.to, year,
    source: seeded ? SRC_OWN : SRC_ATLAS, seeded, href: regionHref(snap, region),
  };
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* The markup of one note, as components/EraNote.astro draws it (the node test holds the component to these attributes). */
export function renderEra(era) {
  if (!era) return "";
  const src = era.href
    ? `<a class="era-src" href="${esc(era.href)}" rel="noopener">${esc(era.source)}</a>`
    : `<span class="era-src">${esc(era.source)}</span>`;
  return `<span class="era-note" data-era="${esc(era.id)}" data-era-year="${esc(era.year)}"><span class="era-pre">· At the time: </span>`
    + `<span class="era-lab">${esc(era.label)}</span> ${src}</span>`;
}
