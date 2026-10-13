/* What a people page decides before it draws anything, in one place.
 *
 * Eight archives draw a person and each one decided these things for itself:
 * which section comes first, what a date looks like, what a source is called,
 * whether a surname is capitalised, who may be shown. The answers drifted
 * (measured on the built sites, 13 October 2026):
 *
 *   dates     Falco prints «13 Dec 1854», «b. Dec 13 1854» and «1813 – June 8
 *             1876» in the SAME chart; Lerena prints «b. 1876-10-01»; Booyzen
 *             mixes «3 Mar 1843» and "3 March 1843" on 338 of its 369 person
 *             pages. Falco's chart dates carry no label at all, and are the date
 *             of the ACT that names someone, so a parent's chart date can be
 *             the day his child was born, and reads as his own birth.
 *   sources   «register», «read», «record», «doc» and «a record read here» all
 *             mean one thing; «index» means three different things in three
 *             archives; «tree», «lore» and «Testimony» are one thing under
 *             three labels. See PERSON-PAGE-SPEC.md, section 5.
 *   names     Lerena prints the surname in capitals (689 of 692 pages), and a
 *             qualifier of up to 80 characters inside the h1.
 *
 * So this file holds the decisions and nothing else. NO MARKUP, NO DATA IMPORTS,
 * NO ARCHIVE NAMES: it takes values in and returns values out, so node can test
 * it without a build (kit/tools/checkperson_logic.mjs) and a page that is not
 * Astro can use it.
 *
 * WHAT IT REFUSES TO DECIDE. Which of the five grades an INDEX ENTRY is, whether
 * Lerena keeps capital surnames, and whether Booyzen's mega-pages are split.
 * Those are the owner's. The tables below carry them as options, with the
 * current recommendation named, and every one is a parameter.
 *
 * UNKNOWN INPUT IS VISIBLE, NEVER A KIND DEFAULT. A source word this file does
 * not know comes back as source "unmarked" with a label that says so, not as
 * "read" or "tree": the Evidence component learned that lesson with `conn: "no"`
 * rendering as «Family», and this is the same trap one level down.
 */

/* ---------------------------------------------------------------- sections */

/* The fixed order, and the one heading each section is allowed to wear. `id` is
   the anchor, so a link to #sources lands in the same place in every archive. */
export const PERSON_SECTIONS = [
  { id: "family",    heading: "Family",                     required: true  },
  { id: "record",    heading: "What the record says",       required: true  },
  { id: "sources",   heading: "Where this comes from",      required: true  },
  { id: "namesakes", heading: "Others of the same name",    required: false },
  { id: "media",     heading: "Photographs and papers",     required: false },
  { id: "notes",     heading: "Notes and corrections",      required: false },
];
export const SECTION_BY_ID = Object.fromEntries(PERSON_SECTIONS.map((s) => [s.id, s]));

/* ---------------------------------------------------------------- provenance */

/* Two different questions were being answered with one word:
     GRADE   how well is a CLAIM evidenced      documented / probable / inferred / family / disputed
     SOURCE  where did this LINK come from      read / indexed / scanned / tree / inferred / disputed / none
   plus a fact that is neither: membership of the direct line, which is a result
   argued on /direct-line/ and not evidence of anything. It is a flag here
   (`line`), drawn as a bar beside the node, so it no longer takes the border
   that a source should have. */
export const SOURCES = {
  read:     { label: "a record read here",        cls: "via-read"     },
  indexed:  { label: "an index entry, not read",  cls: "via-indexed"  },
  scanned:  { label: "image held, not yet read",  cls: "via-scanned"  },
  tree:     { label: "family tree, unverified",   cls: "via-tree"     },
  inferred: { label: "inferred",                  cls: "via-inferred" },
  disputed: { label: "disputed",                  cls: "via-disputed" },
  none:     { label: "named here only",           cls: "via-none"     },
  unmarked: { label: "unmarked: source word not recognised", cls: "via-unmarked" },
};

/* Every older word, folded in rather than broken. Keys are lower-cased and
   trimmed. «line» is deliberately NOT here: it is a flag, see above. */
const SOURCE_ALIAS = {
  read: "read", register: "read", "a register read here": "read", "a record read here": "read",
  record: "read", doc: "read", documented: "read", "read from the image": "read",
  index: "indexed", indexed: "indexed", "in an index": "indexed", "index entry": "indexed",
  scanned: "scanned", "scanned, not read": "scanned", image: "scanned",
  tree: "tree", "family tree": "tree", "from the tree": "tree", "tree only": "tree",
  lore: "tree", testimony: "tree", told: "tree", family: "tree",
  inf: "inferred", inferred: "inferred", "best candidate": "inferred", probable: "inferred",
  disputed: "disputed", dis: "disputed", disp: "disputed", contested: "disputed",
  none: "none", "": "none", "named here only": "none", "not published here": "none", open: "none",
};

/* `line` arrives as a source word in every archive. Peel it off. */
export function readSource(raw) {
  const k = String(raw ?? "").trim().toLowerCase();
  if (k === "line" || k === "direct line" || k === "the direct line") return { source: "none", line: true, known: true };
  const hit = SOURCE_ALIAS[k];
  if (hit) return { source: hit, line: false, known: true };
  return { source: "unmarked", line: false, known: false };
}

/* Which grade does a SOURCE suggest? Provisional, and null where the owner has
   not decided (PERSON-PAGE-SPEC.md, decision 3): an index entry and an image
   held are the two the archives treat three different ways. */
export const GRADE_HINT = {
  read: "documented", tree: "family", inferred: "inferred", disputed: "disputed",
  indexed: null, scanned: null, none: null, unmarked: null,
};

/* ---------------------------------------------------------------- dates */

const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const MONTH = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const MON_IDX = Object.fromEntries(MON.map((m, i) => [m.toLowerCase(), i]));
Object.assign(MON_IDX, Object.fromEntries(MONTH.map((m, i) => [m.toLowerCase(), i])), { sept: 8 });

/* Parse the shapes this estate actually holds. Returns {y, m, d, circa, ok}
   where m is 0-11 and either of m, d may be null (a year, or a month and year).
   Shapes seen: 1854 · c. 1854 · 13 Dec 1854 · 13 December 1854 · Dec 13 1854 ·
   Dec 13, 1854 · 5 JUL 1767 · 1876-10-01 · 1950-Mar-19 · 13/12/1854 (read as d/m/y,
   the estate's order, never m/d/y). Anything else is {ok:false}: it is shown as
   it was written, not guessed at. */
export function parseDate(raw) {
  if (raw == null) return { ok: false, empty: true };
  if (typeof raw === "number") return { y: raw, m: null, d: null, circa: false, ok: raw > 0 };
  let s = String(raw).trim();
  if (!s || /^(—|-|–|unknown|living)$/i.test(s)) return { ok: false, empty: true };
  let circa = false;
  const c = /^(c\.?|ca\.?|abt\.?|about|circa|~)\s*/i.exec(s);
  if (c) { circa = true; s = s.slice(c[0].length); }
  let m;
  if ((m = /^(\d{4})$/.exec(s))) return { y: +m[1], m: null, d: null, circa, ok: true };
  if ((m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s))) return { y: +m[1], m: +m[2] - 1, d: +m[3], circa, ok: +m[2] >= 1 && +m[2] <= 12 };
  if ((m = /^(\d{4})-([A-Za-z]{3,4})-(\d{1,2})$/.exec(s)) && MON_IDX[m[2].toLowerCase()] != null) return { y: +m[1], m: MON_IDX[m[2].toLowerCase()], d: +m[3], circa, ok: true };
  if ((m = /^(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})$/.exec(s)) && MON_IDX[m[2].toLowerCase()] != null) return { y: +m[3], m: MON_IDX[m[2].toLowerCase()], d: +m[1], circa, ok: true };
  if ((m = /^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$/.exec(s)) && MON_IDX[m[1].toLowerCase()] != null) return { y: +m[3], m: MON_IDX[m[1].toLowerCase()], d: +m[2], circa, ok: true };
  if ((m = /^([A-Za-z]{3,9})\.?\s+(\d{4})$/.exec(s)) && MON_IDX[m[1].toLowerCase()] != null) return { y: +m[2], m: MON_IDX[m[1].toLowerCase()], d: null, circa, ok: true };
  if ((m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s)) && +m[2] >= 1 && +m[2] <= 12) return { y: +m[3], m: +m[2] - 1, d: +m[1], circa, ok: true };
  return { ok: false, text: String(raw) };
}

/* One written form. style "short" → 13 Dec 1854 (charts, tables, facts);
   "long" → 13 December 1854 (prose); "year" → 1854. Unparseable text is
   returned unchanged and `ok` says so, so the caller can show it AND count it. */
export function fmtDate(raw, style = "short") {
  const p = parseDate(raw);
  if (p.empty) return { text: "", ok: true, empty: true };
  if (!p.ok) return { text: p.text ?? String(raw), ok: false };
  const pre = p.circa ? "c. " : "";
  if (style === "year" || p.m == null) return { text: pre + p.y, ok: true, year: p.y };
  const mon = style === "long" ? MONTH[p.m] : MON[p.m];
  return { text: pre + (p.d != null ? p.d + " " : "") + mon + " " + p.y, ok: true, year: p.y };
}

/* «1854–1920», with an en dash and no spaces; «b. 1854»; «d. 1920»; nothing at
   all when neither is known. A single date is NEVER printed without its label:
   Falco's unlabelled chart dates are the proof of why. `years` true prints the
   years only (chart nodes), false prints the full dates (the header line). */
export function lifespan(born, died, { years = true } = {}) {
  const b = fmtDate(born, years ? "year" : "short"), d = fmtDate(died, years ? "year" : "short");
  if (b.text && d.text) return `${b.text}–${d.text}`;
  if (b.text) return `b. ${b.text}`;
  if (d.text) return `d. ${d.text}`;
  return "";
}

/* ---------------------------------------------------------------- living */

const YEAR = /\b(1[5-9]\d\d|20\d\d)\b/;
export function yearOf(v) {
  if (typeof v === "number") return v;
  const m = YEAR.exec(String(v ?? ""));
  return m ? Number(m[1]) : null;
}

/* The estate rule, matching checkliving.py: a birth MORE than `presumeDeadAfter`
   years ago is presumed a death (strict >), anything later is presumed a life,
   and a person is alive if the archive says so in any of the ways it says it.
   `presumeDeadAfter` is passed in because the one source of the number is
   kit/data/living-words.json and a pure function does not import data. */
export function isLiving(p, { now = new Date().getFullYear(), presumeDeadAfter = 80 } = {}) {
  if (!p) return false;
  if (p.living === true || p.presumedLiving === true) return true;
  if (p.living === false) return false;
  const said = String(p.born ?? "").trim().toLowerCase();
  if (said === "living" || said === "alive") return true;
  if (yearOf(p.died) != null || p.died === true) return false;
  const by = yearOf(p.born);
  if (by == null) return false;                 // no birth, no death: the archive's own flag decides, not a guess
  return now - by <= presumeDeadAfter;
}

/* ---------------------------------------------------------------- names */

const PARTICLE = new Set(["de","di","da","del","della","dei","degli","van","von","der","den","le","la","du","dos","das","do","y","e","of","the"]);
/* «Severa FERNANDEZ (m. Alejandro LERENA the younger, 1854)» →
   { name: "Severa FERNANDEZ", qualifier: "m. Alejandro LERENA the younger, 1854" }
   The qualifier tells two women of one name apart and belongs in a line under
   the heading, not inside the h1 where a search result truncates it. */
export function splitQualifier(full) {
  const s = String(full ?? "").trim();
  const m = /^(.*?)\s*\((.+)\)\s*$/.exec(s);
  return m ? { name: m[1].trim(), qualifier: m[2].trim() } : { name: s, qualifier: "" };
}

/* style "asRecorded" keeps every letter as the archive holds it; "titleCase"
   lowers an ALL-CAPS token and keeps particles lower-case and the apostrophe
   forms (D'ARCY → D'Arcy, O'BRIEN → O'Brien, MCDONALD is left as McDonald only if
   `exceptions` says so). Diacritics are never touched. Decision 4 in the spec
   is whether Lerena keeps capitals; this function makes either answer cheap. */
export function displayName(name, { style = "titleCase", exceptions = {} } = {}) {
  const s = String(name ?? "");
  if (style === "asRecorded") return s;
  return s.split(/(\s+)/).map((tok, i, all) => {
    if (/^\s+$/.test(tok) || !tok) return tok;
    if (exceptions[tok]) return exceptions[tok];
    const letters = tok.replace(/[^A-Za-zÀ-ÖØ-öø-ÿĀ-ž]/g, "");
    if (letters.length < 2 || letters !== letters.toUpperCase()) return tok;         // already mixed case, or an initial
    const lower = tok.toLowerCase();
    const first = all.findIndex((t) => t.trim()) === i;
    if (!first && PARTICLE.has(lower)) return lower;
    return lower.replace(/(^|['’\-])(\p{L})/gu, (m, a, b) => a + b.toUpperCase());
  }).join("");
}

/* ---------------------------------------------------------------- stubs */

/* A stub is a page that has a name and nothing else. It still gets a page (a
   link to it exists), but it says what it is instead of drawing four empty
   cards. Measured 13 October 2026 by non-boilerplate words under 40: Mazza 356
   of 712, Falco 167 of 936, Blazevic 279 of 1,904, Defranceski 255 of 1,961. */
export function stubReason(p) {
  if (!p) return null;
  const rel = ["parents", "spouses", "children", "siblings"].reduce((n, k) => n + ((p.relations && p.relations[k]) || []).length, 0);
  const ev = (p.events || []).length, src = (p.sources || []).length;
  if (ev === 0 && src === 0 && rel === 0) return "name-only";
  if (ev === 0 && src === 0) return "relations-only";
  if (ev === 0 && rel === 0) return "sources-only";
  return null;
}

/* Why a chart is empty, as a code the page turns into a sentence. A chart that
   draws nothing makes a claim in silence (traps.md), so there is always one. */
export function chartEmptyReason(p, { nameHref = null } = {}) {
  const rel = p?.relations || {};
  const all = ["parents", "spouses", "children", "siblings"].flatMap((k) => rel[k] || []);
  if (all.length === 0) return nameHref ? "name-level" : "none-recorded";
  if (all.every((r) => r.living || r.gap)) return "living-withheld";
  return null;
}
export const EMPTY_TEXT = {
  "none-recorded": "No parent, spouse, child or sibling is recorded for this person in this archive.",
  "living-withheld": "Everyone this person is connected to is living, and living people are not drawn.",
  "name-level": "This archive records kin against a name rather than against this person, so no chart is drawn here; the name page gathers everyone who bore it.",
};

/* ---------------------------------------------------------------- structured data */

/* What the existing JsonLd.astro can carry in `about`. A living person yields
   null, always: a search engine must not be handed a birth date this archive
   would not print. Only fields the page itself displays are included. */
export function personAbout(p, opts = {}) {
  if (!p || isLiving(p, opts)) return null;
  const b = fmtDate(p.born, "short"), d = fmtDate(p.died, "short");
  const iso = (v) => { const x = parseDate(v); if (!x.ok || x.circa) return undefined; return x.m == null ? String(x.y) : `${x.y}-${String(x.m + 1).padStart(2, "0")}${x.d != null ? "-" + String(x.d).padStart(2, "0") : ""}`; };
  return {
    name: p.name,
    birthDate: iso(p.born), deathDate: iso(p.died),
    birthPlace: p.birthPlace || undefined, deathPlace: p.deathPlace || undefined,
    _shown: { born: b.text || undefined, died: d.text || undefined },
  };
}

/* The head of the page, decided once. `noindex` is true for anyone living — the
   page may exist, the search engine may not see it. The description of a living
   person is a fixed sentence, never built from their record, so nothing about
   them can reach a snippet. Title and description are what Base.astro takes. */
export const LIVING_SENTENCE = "A living member of the family. This archive names living people and says how they are related, and publishes nothing else about them.";
export function personMeta(p, { style = "titleCase", exceptions = {}, siteName = "", ...opts } = {}) {
  const nm = splitQualifier(displayName(p?.name, { style, exceptions }));
  const living = isLiving(p, opts);
  const life = living ? "" : lifespan(p?.born, p?.died);
  const suffix = siteName ? ` — ${siteName}` : "";
  return {
    name: nm.name, qualifier: nm.qualifier, living,
    title: nm.name + (life ? `, ${life}` : "") + suffix,
    description: living ? LIVING_SENTENCE : (p?.lede || [life, nm.qualifier].filter(Boolean).join(" · ") || nm.name),
    noindex: living,
    about: living ? null : personAbout(p, opts),
  };
}
