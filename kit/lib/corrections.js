/* corrections.js — what the Corrections page and /whats-new/ must agree on, so that a correction on What's new can link to THAT correction.
 *
 * Before this, a "Corrected" card on What's new linked to /corrections/ and nowhere else: the page has hundreds of entries and the reader had to
 * find theirs by eye. Both sides now compute the same anchor from the archive's own correction row (its date and its headline), so the link lands on
 * the entry. The archive does not choose or store ids: it passes its rows through corrIdMap() and puts the id on the entry it draws.
 *
 * Pure functions, no DOM, no locale: they run in the build and in node kit/tools/corrections_logic.mjs. */
import { parseWhen } from "./when.js";

/* the field names the eight archives use for a correction's date and headline (the same lists lib/pulse.js reads: cwhen, cwhat) */
const WHEN = ["when", "date"], WHAT = ["what", "what_was_said", "was"];
const first = (r, keys) => { for (const k of keys) if (r && r[k] != null && r[k] !== "") return r[k]; return ""; };

/* FNV-1a, 32 bit: no dependency, same answer in node and the browser */
const fnv = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h >>> 0; };
const norm = (s) => String(s == null ? "" : s).replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().slice(0, 240);

/* the anchor of each correction row: "c-2026-11-17-1k3f9a" (the day, then a hash of the headline). Two rows with the same day and headline get
   -2, -3 in the order given, so pass the rows in the archive's FILE order, not a sorted copy. Returns a Map from each row object to its id. */
export function corrIdMap(rows) {
  const map = new Map(), seen = new Map();
  for (const r of rows || []) {
    if (!r || typeof r !== "object") continue;
    const w = parseWhen(first(r, WHEN));
    const base = "c-" + (w ? w.iso : "undated") + "-" + fnv(norm(first(r, WHAT))).toString(36);
    const n = (seen.get(base) || 0) + 1; seen.set(base, n);
    map.set(r, n === 1 ? base : base + "-" + n);
  }
  return map;
}

/* newest first. A row whose date cannot be read (Mazza's undated rows, a record year) goes after the dated ones, in the order it came; rows on the
   same day keep the order they came in (the archive may put the serious ones first within a day). `whenOf` says where a row keeps its date. */
export function byDateDesc(rows, whenOf = (r) => r && r.when) {
  const keyed = (rows || []).map((r, i) => { const w = parseWhen(whenOf(r)); return { r, i, iso: w ? w.iso : "" }; });
  if (!keyed.some((k) => k.iso)) return [...(rows || [])];
  keyed.sort((a, b) => (a.iso === b.iso ? a.i - b.i : !a.iso ? 1 : !b.iso ? -1 : a.iso < b.iso ? 1 : -1));
  return keyed.map((k) => k.r);
}

/* WHO, WHERE and WHEN a correction is about, read out of the sentences the archive has already written (its rendered HTML), so a long paragraph
   opens with the people, the places and the dates in it, as links and chips, before the prose. Nothing is invented: a person or a place is an
   <a> the archive already linked (a path with /person/, /people/ or /who/ is a person; /place/ or /places/ is a place), a date is a date written
   in the text. A work date (2020 or later: "read on 16 November 2026") is when the correction was made, not what it is about, and is left out. */
const MON = "(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)";
const DATE = new RegExp("\\b(?:1[0-9]{3}|20[01][0-9])\\s*[–-]\\s*(?:1[0-9]{3}|20[01][0-9])\\b|\\b(?:\\d{1,2}\\s+" + MON + "\\.?\\s+\\d{4}|" + MON + "\\.?\\s+\\d{1,2},?\\s+\\d{4}|" + MON + "\\.?\\s+\\d{4})\\b|\\b(1[0-9]{3}|20[01][0-9])\\b", "g");
const textOf = (h) => String(h || "").replace(/<[^>]*>/g, " ").replace(/&amp;/g, "&").replace(/&[a-z]+;/g, " ").replace(/\s+/g, " ").trim();
/* what a date is the date OF, from the words just before it: "death" (died, buried, burial, d.), "birth" (born, baptised, christened, b.), "marriage"
   (married, wedding). The nearest of these words in the clause wins; none, none. */
const KINDS = [["death", /\b(?:died|dies|buried|burial|burials|dead|d\.)(?=\W|$)/gi], ["birth", /\b(?:born|birth|births|baptis\w*|baptiz\w*|christen\w*|b\.)(?=\W|$)/gi], ["marriage", /\b(?:married|marriage|marriages|wedding|weddings)(?=\W|$)/gi]];
export function kindBefore(before) {
  const w = String(before || "").split(/[;()]|\.\s/).pop();
  let best = "", at = -1;
  for (const [kind, re] of KINDS) {
    for (const m of w.matchAll(re)) {
      /* the word must lead straight to the date: not 28+ characters back, and not across "book", "register", "entries" (a baptism BOOK of 1764 is not a birth) */
      const tail = w.slice(m.index + m[0].length);
      /* "dead" is a death only straight before its date ("born 1934, dead October 1955", "dead in 1955"), never in "the dead man's letter" */
      if (/^dead$/i.test(m[0]) && !/^\s*(?:(?:in|on)\s+)?$/i.test(tail)) continue;
      if (tail.length > 28 || /\b(?:book|books|register|registers|entries|entry|index|volume|records?|rows?)\b/i.test(tail)) continue;
      if (m.index > at) { at = m.index; best = kind; }
    }
  }
  return best;
}
export function factsOf(...htmls) {
  const people = new Map(), places = new Map(), dates = new Map(), sources = new Map();
  for (const h of htmls) {
    const html = String(h || "");
    for (const m of html.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)) {
      const attrs = m[1], hm = /\bhref="([^"]*)"/.exec(attrs); if (!hm) continue;
      const full = hm[1], href = full.split("#")[0], name = textOf(m[2]);
      /* a link to the record the correction rests on: a record link the archive drew (class lk-rec, as the linking standard marks it) or any address
         off the site (a FamilySearch image, an archive's catalogue). Its label is the link's own title (\"FamilySearch image 3:1:...\"), else its words. */
      if (/\blk-rec\b/.test(attrs) || /^https?:\/\//.test(full)) {
        const t = (/\btitle="([^"]*)"/.exec(attrs) || [])[1] || name;
        if (t && full && !sources.has(full)) sources.set(full, t.length > 70 ? t.slice(0, 68) + "…" : t);
        continue;
      }
      if (!name || name.length > 90) continue;
      /* a name that several people bear (class lk-shared, the autolinker's and namelinks.js's) is marked, so the chip says it opens a list */
      if (/\/(person|people|who)\/[^/]+/.test(href)) { if (!people.has(href)) people.set(href, { name, shared: /\blk-shared\b/.test(attrs) }); }
      else if (/\/places?\/[^/]+/.test(href)) {
        /* the flags the place link carries (placelinks.js draws them inside the link), so the chip can show the same flags */
        const flags = [...m[2].matchAll(/<img\b[^>]*\bsrc="([^"]*)"/g)].map((x) => x[1]), title = (/\btitle="([^"]*)"/.exec(attrs) || [])[1] || "";
        if (!places.has(href)) places.set(href, { name, flags, title });
      }
    }
    /* dates are read from the text; the word just before one says what it is a date OF (died / born / married), so the chip can wear the
       genealogist's mark for it. Only the clause the date is in is looked at (up to the last ; . or bracket before it), and the nearest word wins. */
    const plain = textOf(html);
    for (const m of plain.matchAll(DATE)) {
      const t = m[0].trim(), y = +(t.match(/\d{4}/) || [0])[0];
      if (y >= 2020 || y < 1000) continue;
      /* a year inside a range ("1764–1791") is the years of a book, not of an event */
      const inRange = /\d\s*[–-]\s*$/.test(plain.slice(Math.max(0, m.index - 3), m.index)) || /^\s*[–-]\s*\d/.test(plain.slice(m.index + t.length, m.index + t.length + 3));
      const k = t.toLowerCase(), kind = inRange || /[–-]/.test(t) ? "" : kindBefore(plain.slice(Math.max(0, m.index - 60), m.index));
      const had = dates.get(k);
      if (!had) dates.set(k, { text: t, kind }); else if (!had.kind && kind) had.kind = kind;
    }
  }
  /* a bare year that is already inside a longer date shown ("1858" beside "1 February 1858") is the same date: show the longer */
  const list = [...dates.values()];
  const long = list.filter((d) => d.text.length > 4);
  const shown = list.filter((d) => !(/^\d{4}$/.test(d.text) && long.some((l) => l.text.includes(d.text))));
  return { sources: [...sources].map(([href, name]) => ({ href, name })), people: [...people].map(([href, v]) => ({ href, name: v.name, shared: v.shared })), places: [...places].map(([href, v]) => ({ href, name: v.name, flags: v.flags, title: v.title })), dates: shown.slice(0, 8) };
}
