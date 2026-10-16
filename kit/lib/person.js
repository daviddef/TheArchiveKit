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
 * WHAT THE OWNER HAS RULED (16 October 2026), and what is therefore fixed here
 * rather than offered as an option: the evidence vocabulary is two axes plus a flag
 * (five grades for claims, seven source words for links, the direct line as a bar;
 * an index entry and an image held stay UNGRADED); Lerena's capitalised surnames are
 * title-cased on display with the data unchanged and the qualifier out of the h1.
 * The other two rulings (Booyzen's split, Defranceschi's two page kinds) are about
 * what an archive builds, not about anything this file decides.
 *
 * THE LIVING RULE IS NOT OPINION, IT IS THE ESTATE'S STANDARD, version 2 (16 October
 * 2026): see "living" below. It is the JavaScript twin of kit/tools/living_rule.py,
 * and both are held to ONE list of cases, kit/data/living-rule-cases.json, so they
 * cannot disagree without a test failing.
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

/* THE TWO AXES, RULED 16 October 2026 (PERSON-PAGE-SPEC.md, section 13, ruling 3):
     GRADES   five words for a CLAIM
     SOURCES  seven words for a LINK (the seven keys below; `unmarked` is not a word,
              it is the visible refusal to guess at one this file does not know)
     the direct line is a BAR, never a grade and never a source
   An INDEX ENTRY and an IMAGE HELD stay UNGRADED: they say where a link came from
   and that nobody has read it, which is not a level of proof. */
export const GRADES = ["documented", "probable", "inferred", "family", "disputed"];
export const SOURCE_KEYS = ["read", "indexed", "scanned", "tree", "inferred", "disputed", "none"];
export const UNGRADED_SOURCES = ["indexed", "scanned"];

/* Which grade does a SOURCE suggest? A hint for an archive that has not said, never
   applied by a component. Null for an index entry and an image held BY RULING, and
   for «named here only» and an unrecognised word because nothing is evidenced. */
export const GRADE_HINT = {
  read: "documented", tree: "family", inferred: "inferred", disputed: "disputed",
  indexed: null, scanned: null, none: null, unmarked: null,
};
/* May a chip draw a grade beside this source? Not beside an index entry or an image
   held: those are ungraded by ruling, so a grade passed with them is not drawn. */
export function gradeAllowed(source) {
  return !UNGRADED_SOURCES.includes(source);
}

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

/* DAVID'S LIVING-PEOPLE STANDARD, version 2 (16 October 2026). One definition in
   Python (kit/tools/living_rule.py), this is the same one in JavaScript. The cases
   that pin both are in kit/data/living-rule-cases.json and are read by BOTH
   self-tests (living_rule_selftest.py, checkperson_logic.mjs).

     living       born 80 years ago or less BY YEAR (this year minus the birth year,
                  80 or less) with no death or burial recorded
     dead         any recorded death or burial, dated or not
     not living   a citation from a PUBLIC record source (kit/data/public-sources.json;
                  FamilySearch always counts, a user-built tree filed under MyHeritage
                  research does not); and no birth year at all
     a living person shows NAME, RELATIONSHIPS and FULL TOWN AND COUNTRY, nothing else
     held out     (not published at all) an UNDATED person with a living parent, and the
                  people promised privacy, by id. A child with a KNOWN birth year under
                  18 is NOT held out: she follows the standard like any living person

   What this replaces, deliberately: `living`/`presumedLiving` flags set by hand, a
   birth field that says «living», and the 100-year bound. They are NOT read. A flag
   that disagrees with the dates is a mistake to be fixed in the data, and a page
   must never be more generous than the rule because an archive said so. */
export const LIVING_YEARS = 80;
/* An undated parent whose youngest known child was born this many years ago or less is living (17 Oct 2026). */
export const CHILD_LIVING_YEARS = 60;

/* `sources` is the parsed kit/data/public-sources.json. A pure function does not
   import data, so the caller passes it; with citations and no list this THROWS
   rather than guess, because a silent default is exactly how the two copies of a
   rule come apart. FamilySearch counts whatever the list says. */
export function publicSource(citations, sources) {
  const list = (citations || []).map((c) => String(c).toLowerCase());
  if (list.some((s) => s.includes("familysearch"))) return true;
  if (list.length === 0) return false;
  if (!sources || !Array.isArray(sources.providers) || !Array.isArray(sources.excluded)) {
    throw new Error("living rule: pass kit/data/public-sources.json as `sources` (citations were given and cannot be judged without it)");
  }
  const providers = sources.providers.map((x) => String(x).toLowerCase());
  const excluded = sources.excluded.map((x) => String(x).toLowerCase());
  for (const s of list) {
    if (excluded.some((x) => s.includes(x))) continue;
    if (providers.some((x) => s.includes(x))) return true;
  }
  return false;
}

/* The rule on its own inputs, positional like living_rule.py. */
export const livingRule = {
  publicSource,
  recentChild(youngestChildYear, todayYear = null) {
    if (youngestChildYear == null) return false;
    return ((todayYear || new Date().getFullYear()) - Number(youngestChildYear)) <= CHILD_LIVING_YEARS;
  },
  isLiving(birthYear, recordedDead, citations = [], todayYear = null, sources = null, youngestChildYear = null, saidLiving = false) {
    if (recordedDead) return false;
    if (publicSource(citations, sources)) return false;
    if (birthYear == null) return Boolean(saidLiving) || livingRule.recentChild(youngestChildYear, todayYear);
    return ((todayYear || new Date().getFullYear()) - Number(birthYear)) <= LIVING_YEARS;
  },
  possibleMinor(birthYear, recordedDead, citations = [], parentLiving = false, todayYear = null, sources = null, youngestChildYear = null) {
    if (recordedDead || publicSource(citations, sources)) return false;
    if (birthYear != null) return false;
    if (livingRule.recentChild(youngestChildYear, todayYear)) return false;
    return Boolean(parentLiving);
  },
  isHeldOut(personId, birthYear, recordedDead, citations = [], parentLiving = false, heldIds = [], todayYear = null, sources = null, youngestChildYear = null) {
    if (new Set((heldIds || []).map(String)).has(String(personId))) return true;
    return livingRule.possibleMinor(birthYear, recordedDead, citations, parentLiving, todayYear, sources, youngestChildYear);
  },
};

const YEAR = /\b(1[5-9]\d\d|20\d\d)\b/;
export function yearOf(v) {
  if (typeof v === "number") return v;
  const m = YEAR.exec(String(v ?? ""));
  return m ? Number(m[1]) : null;
}

/* From a person (or a relative's row) to the rule's inputs. The fields an archive's
   adapter may set: born (any date shape or a year), died, buried, deathPlace,
   `dead: true` or `deathRecorded: true` for an UNDATED death or burial, and
   `citations` (strings) and/or `sources` (strings or {provider,url,title}). */
export function birthYearOf(p) { return p ? (p.birthYear ?? yearOf(p.born)) : null; }
const NO_DEATH = /^(|living|alive|—|-|–|\?|unknown|none)$/i;
export function recordedDead(p) {
  if (!p) return false;
  if (p.dead === true || p.deathRecorded === true) return true;
  for (const k of ["died", "buried"]) {
    const v = p[k];
    if (v === true) return true;
    if (v != null && v !== false && !NO_DEATH.test(String(v).trim())) return true;
  }
  return Boolean(p.deathPlace && String(p.deathPlace).trim());
}
export function citationsOf(p) {
  if (!p) return [];
  const one = (x) => (x == null ? "" : typeof x === "object" ? [x.provider, x.url, x.title, x.name, x.source, x.label].filter(Boolean).join(" ") : String(x));
  return [...(p.citations || []), ...(p.sources || [])].map(one).filter(Boolean);
}

/* The rule, applied to a person. `now` and `sources` are passed in. */
export function isLiving(p, { now = null, sources = null } = {}) {
  if (!p) return false;
  return livingRule.isLiving(birthYearOf(p), recordedDead(p), citationsOf(p), now, sources, p.youngestChildYear ?? null, p.saidLiving === true);
}
/* Held out of the archive entirely: promised by id, or undated with a living parent.
   `parentLiving` is the caller's knowledge, or the row's own `parentLiving`. */
export function isHeldOut(p, { now = null, sources = null, heldIds = [], parentLiving = false } = {}) {
  if (!p) return false;
  return livingRule.isHeldOut(p.id, birthYearOf(p), recordedDead(p), citationsOf(p), parentLiving || p.parentLiving === true, heldIds, now, sources, p.youngestChildYear ?? null);
}
/* A relative's row that must not be drawn at all: held out by the rule, flagged by
   the adapter, or the old «withheld» placeholder (which would reveal that a held-out
   person exists, so it is gone). */
export function heldOutRow(r, opts = {}) {
  if (!r) return false;
  if (r.gap || r.heldOut === true) return true;
  return isHeldOut(r, opts);
}

/* THE PLACE OF A LIVING PERSON: «Town, Country» and nothing else. `town` and `country`
   are preferred; a single `place` string is accepted as written. If any part looks like
   an address or an institution the place is REFUSED (text empty, refused true) rather
   than shown: the adapter must reduce it to the town and country, and the page records
   that it had to refuse. Twin of living_rule.address_like, held to the same cases. */
const INSTITUTION = /\b(hospital|clinic|infirmary|hospice|sanatorium|nursing|care home|rest home|retirement|aged care|maternity|medical cent(?:re|er))\b/i;
const STREET = /(?:^|[,;])\s*[^,;]*\S\s+(?:street|st|road|rd|avenue|ave|lane|ln|boulevard|blvd|highway|hwy)\.?\s*(?=[,;]|$)/i;
export function placeIsAddressLike(place) {
  const s = String(place ?? "");
  return /\d/.test(s) || INSTITUTION.test(s) || STREET.test(s);
}
export function livingPlace(p) {
  const given = p?.town || p?.country ? [p.town, p.country].filter(Boolean).join(", ") : String(p?.place ?? "").trim();
  if (!given) return { text: "", refused: false };
  if (placeIsAddressLike(given)) return { text: "", refused: true };
  return { text: given, refused: false };
}

/* The relations a page may publish: every row the rule holds out is removed, and a
   living person's UNDATED children are held out (an undated person with a living
   parent). A child with a known birth year stays: it follows the standard. */
export function publishedRelations(p, opts = {}) {
  const rel = p?.relations || {};
  const selfLiving = isLiving(p, opts);
  const keep = (rows, parentLiving) => (rows || []).filter((r) => !heldOutRow(r, { ...opts, parentLiving }));
  return { parents: keep(rel.parents, false), spouses: keep(rel.spouses, false), children: keep(rel.children, selfLiving),
           siblings: keep(rel.siblings, false), dropped: keep(rel.dropped, false) };
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
   `exceptions` says so). Diacritics are never touched. RULED 16 October 2026 (ruling 4): titleCase is
   how a name is DISPLAYED, the data is never changed, and `asRecorded` stays for any
   page that wants the capitals. */
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
   draws nothing makes a claim in silence (traps.md), so there is always one.
   Counted on what may be PUBLISHED: a relative the living rule holds out is not
   drawn, so it must not make the chart look as though somebody is. The old
   «living-withheld» reason is gone: living relatives are drawn by name now. */
export function chartEmptyReason(p, { nameHref = null, ...opts } = {}) {
  const rel = publishedRelations(p, opts);
  const all = ["parents", "spouses", "children", "siblings", "dropped"].flatMap((k) => rel[k] || []);
  if (all.length === 0) return nameHref ? "name-level" : "none-recorded";
  return null;
}
export const EMPTY_TEXT = {
  "none-recorded": "No parent, spouse, child or sibling is published for this person in this archive.",
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

/* The head of the page, decided once. `noindex` is true for anyone living: the
   page exists, the search engine does not see it, and it is out of the sitemap and
   the search index. The description of a living person is the standard's one fixed
   sentence, never built from the record, so nothing about them can reach a
   snippet. A living person's title is the name alone and the qualifier is dropped
   (it can hold a spouse and a year). Title and description are what Base.astro takes. */
export const LIVING_SENTENCE = "A living person (80 or younger, with no death recorded) is named with their relationships and their town and country, and nothing more.";
export function personMeta(p, { style = "titleCase", exceptions = {}, siteName = "", ...opts } = {}) {
  const nm = splitQualifier(displayName(p?.name, { style, exceptions }));
  const living = isLiving(p, opts);
  const life = living ? "" : lifespan(p?.born, p?.died);
  const suffix = siteName ? ` — ${siteName}` : "";
  return {
    name: nm.name, qualifier: living ? "" : nm.qualifier, living,
    title: nm.name + (life ? `, ${life}` : "") + suffix,
    description: living ? LIVING_SENTENCE : (p?.lede || [life, nm.qualifier].filter(Boolean).join(" · ") || nm.name),
    noindex: living,
    about: living ? null : personAbout(p, opts),
  };
}
