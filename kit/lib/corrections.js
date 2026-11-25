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
/* the words of a rendered sentence: tags gone, the entities a markdown helper writes (&#39; &quot; &amp; &lt; &gt; &nbsp;, numeric and hex) turned back into the characters */
const ENT = { amp: "&", quot: '"', apos: "'", lt: "<", gt: ">", nbsp: " " };
const textOf = (h) => String(h || "").replace(/<[^>]*>/g, " ")
  .replace(/&#x([0-9a-f]+);/gi, (m, x) => String.fromCodePoint(parseInt(x, 16)))
  .replace(/&#(\d+);/g, (m, d) => String.fromCodePoint(+d))
  .replace(/&([a-z]+);/gi, (m, n) => (ENT[n.toLowerCase()] !== undefined ? ENT[n.toLowerCase()] : " "))
  .replace(/\s+/g, " ").trim();
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

/* ---- the ledger view (26 November 2026): one card per correction, a reading pane, a heartbeat of the days ----
   Pure functions, so they run in the build and in node kit/tools/corrections_logic.mjs. */

/* A correction's grade is each archive's own word (Lerena: serious / minor; Falco: twelve words from major to resolved; Mazza: documented,
   probable...). Only the four that really are a severity get a colour of their own; every other word is "other", one neutral colour, so a status
   is never painted as a danger. `major` is the archive's own name for its gravest grade (the Corrections prop), kept as "serious" when no
   other rule has placed it. */
const TONES = { major: "major", serious: "serious", material: "serious", moderate: "moderate", minor: "minor", slip: "minor" };
export const TONE_ORDER = ["major", "serious", "moderate", "minor", "other"];
export const TONE_LABEL = { major: "Major", serious: "Serious", moderate: "Moderate", minor: "Minor", other: "Other" };
export function toneOf(sev, major = "major") {
  const k = String(sev == null ? "" : sev).trim().toLowerCase();
  if (!k) return "other";
  if (TONES[k]) return TONES[k];
  return k === String(major).trim().toLowerCase() ? "serious" : "other";
}

const clip = (s, n) => (s.length > n ? s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…" : s);
const firstSentence = (s) => { const m = /^.+?[.!?](?=\s|$)/.exec(s); return m ? m[0] : s; };
/* what a card says, from the sentences the archive already wrote (rendered HTML):
   title    the claim that was retracted (`was`), or, where an archive puts the whole headline in `kind` (Falco, Defranceschi, Blažević), that;
            where there is no `was`, the first sentence of the answer
   verdict  the answer in a line: the loud opening of `now` (the archive sets it in <strong>) if it has one, else its first sentence.
            Empty when it would only repeat the title. Nothing is written by the kit: every word is the archive's. */
export function cardOf(r, longKind = 48) {
  const kind = String(r && r.kind || "").trim();
  const wasT = textOf(r && r.was), nowT = textOf(r && r.now);
  const loud = /^\s*(?:<p>\s*)?<(strong|b)>\s*(?:<(?:em|i)>)?([\s\S]*?)(?:<\/(?:em|i)>)?\s*<\/\1>/i.exec(String((r && r.now) || ""));
  const loudT = loud ? textOf(loud[2]) : "";
  let title, verdict;
  if (kind.length > longKind) title = clip(kind, 160);
  else if (wasT) title = clip(wasT, 160);
  else title = clip(firstSentence(nowT), 160);
  verdict = loudT.length >= 12 ? loudT : firstSentence(nowT);
  verdict = clip(verdict, 190);
  if (!nowT || verdict === title || title.startsWith(verdict.replace(/…$/, "")) || (!wasT && kind.length <= longKind)) verdict = "";
  return { title, verdict };
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export const longDate = (iso) => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || ""); return m ? `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}` : ""; };
const dayNum = (iso) => Math.round(Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / 864e5);
const dayIso = (n) => new Date(n * 864e5).toISOString().slice(0, 10);

/* The days the corrections were caught, first to last, one bar each (a bar is a week or more where the span is over `max` days), each with how
   many, by tone. Only exact days count: a month alone ("Sept 2026") is not a day. Null when fewer than two different days are dated: a
   heartbeat of one beat says nothing. */
export function heartbeat(rows, whenOf = (r) => r && r.when, majorOf = "major", sevOf = (r) => r && r.sev, max = 120) {
  const pts = [];
  for (const r of rows || []) { const w = parseWhen(whenOf(r)); if (w && w.exact) pts.push({ n: dayNum(w.iso), tone: toneOf(sevOf(r), majorOf) }); }
  if (new Set(pts.map((p) => p.n)).size < 2) return null;
  const lo = Math.min(...pts.map((p) => p.n)), hi = Math.max(...pts.map((p) => p.n));
  const size = Math.max(1, Math.ceil((hi - lo + 1) / max));
  const bars = [];
  for (let s = lo; s <= hi; s += size) {
    const e = Math.min(hi, s + size - 1), tones = {}; let n = 0;
    for (const p of pts) if (p.n >= s && p.n <= e) { tones[p.tone] = (tones[p.tone] || 0) + 1; n++; }
    bars.push({ from: dayIso(s), to: dayIso(e), n, tones });
  }
  return { bars, from: dayIso(lo), to: dayIso(hi), size, peak: Math.max(...bars.map((b) => b.n)) };
}

/* the kinds worth a filter: a short category on most rows ("Birth year"; 60% or more), not a headline sentence on each (Falco puts the whole headline in
   `kind`, and 415 distinct headlines are not a filter). */
export function kindFilterable(rows, longKind = 48) {
  const ks = (rows || []).map((r) => String(r.kind || "").trim()).filter(Boolean);
  if (!ks.length) return false;
  const short = ks.filter((k) => k.length <= longKind).length;
  return short / ks.length >= 0.6 && new Set(ks).size > 1 && new Set(ks).size <= 200;
}
