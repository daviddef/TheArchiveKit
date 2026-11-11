/* THE PULSE: what is new in an archive, and the archive in numbers. Kit version of the Defranceschi prototype (11 November 2026).
 *
 * Nothing here is written by hand and nothing is generated into a file that can go stale: it is computed at BUILD time from the logs the
 * archive already keeps (the search log, the corrections list, the work list) plus the few counts the archive passes in. A finding that
 * is logged shows up by the next build.
 *
 * PURE FUNCTIONS, no imports of archive data: the archive's own src/lib/pulse.js imports its JSON and calls buildPulse(); see
 * kit/docs/whats-new.md. The kit's own test is kit/tools/pulse_logic.mjs.
 *
 * Counts only, and the text of entries that the archive's own log and corrections pages already print (clipped, never rewritten):
 * nothing about a living person that those pages do not already hold, and no person is counted by name.
 */

/* the card kinds of the timeline (Record Atlas's vocabulary): a day's searches fold into ONE research card, each correction is its own */
export const CARD = {
  research: { label: "Research", glyph: "⚑", note: "registers and sources read that day, with what each gave" },
  corrected: { label: "Corrected", glyph: "✓", note: "an earlier claim was withdrawn or fixed" },
};
export const KIND = {
  found: { label: "Found", glyph: "✦", note: "a register or source gave something" },
  corrected: { label: "Corrected", glyph: "✓", note: "an earlier claim was withdrawn or fixed" },
  nil: { label: "Nothing found", glyph: "○", note: "searched, in the terms named, and nothing" },
  partial: { label: "Partly", glyph: "◐", note: "some of it read, some not" },
  blocked: { label: "Blocked", glyph: "■", note: "could not be read (a block, a restriction, not on the film)" },
};

/* the archives have written the same five outcomes with a dozen words (Searched.astro's ALIAS has the same list); a word not here is
   not guessed at: the row is left out of the timeline (it stays on the archive's own log page) */
export const OUTCOME = {
  hit: "found", yield: "found", found: "found",
  nothing: "nil", nil: "nil", miss: "nil", clean: "nil", null: "nil", empty: "nil",
  partial: "partial", part: "partial", mixed: "partial",
  blocked: "blocked", correction: "corrected",
};
const outcomeOf = (word, map) => {
  const w = String(word == null ? "" : word).trim().toLowerCase();
  if (map[w]) return map[w];
  if (/^(no |not there|nothing)/.test(w)) return "nil";
  return null;
};

const MON = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };

/* "2026-11-11", "2026-11", "11 Nov 2026", "5 October 2026", "Sept 2026" (a month alone: day 1, exact false); anything else (a bare record
   year, a sentence) is not a date the work was done on, and returns null */
export function parseWhen(s) {
  const t = String(s == null ? "" : s).trim();
  let m = /^(\d{4})-(\d{2})(?:-(\d{2}))?(?:$|[T\s])/.exec(t);
  if (m) {
    const mo = +m[2];
    if (mo < 1 || mo > 12) return null;
    return { iso: `${m[1]}-${m[2]}-${m[3] || "01"}`, exact: !!m[3] };
  }
  m = /^(?:(\d{1,2})\s+)?([A-Za-z]{3,})\.?\s+(\d{4})$/.exec(t);
  if (!m) return null;
  const mo = MON[m[2].slice(0, 3).toLowerCase()];
  if (mo === undefined) return null;
  const day = m[1] ? +m[1] : 1;
  return { iso: `${m[3]}-${String(mo + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`, exact: !!m[1] };
}

const clean = (s) => String(s == null ? "" : s).replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/[*_`]/g, "").replace(/\s+/g, " ").trim();
export const clip = (s, n) => {
  s = clean(s);
  if (s.length <= n) return s;
  const c = s.slice(0, n), k = c.lastIndexOf(" ");
  return c.slice(0, k > n * 0.6 ? k : n).replace(/[,;:(—\-\s]+$/, "") + "…";
};
const first = (r, keys) => { for (const k of keys) if (r[k] != null && r[k] !== "") return r[k]; return ""; };
/* the log files come as an array, as {rows:[]}, or as {searched:[]}; underscore rows (notes to the reader) are not entries */
export const rowsOf = (x) => {
  const a = Array.isArray(x) ? x : x && Array.isArray(x.rows) ? x.rows : x && Array.isArray(x.searched) ? x.searched : [];
  return a.filter((r) => r && typeof r === "object" && !("_note" in r));
};

/* the field names each archive has used, tried in order; an archive may override any of them in `fields` */
const FIELDS = {
  when: ["when", "date"],
  outcome: ["outcome", "status"],
  what: ["what", "scope", "result", "got"],
  src: ["src", "source"],
  place: ["dest", "where"],
  pages: ["pages"],
  cwhen: ["when", "date"],
  cwhat: ["what", "what_was_said", "was"],
};

/**
 * buildPulse({ searched, corrections, worklist, counts, fields, outcomeMap, logHref, correctionsHref, today })
 *   searched / corrections / worklist: the archive's JSON, whatever its shape (see rowsOf)
 *   counts: { people, sources } the archive passes in (the one thing it knows that no log holds); logged, walked, corrections, done, open are computed
 *   logHref / correctionsHref: where the archive's own pages are ("/searched/", "/corrections/")
 */
export function buildPulse(o = {}) {
  const F = { ...FIELDS, ...(o.fields || {}) };
  const OUT = { ...OUTCOME, ...(o.outcomeMap || {}) };
  const logHref = o.logHref || "/searched/", corHref = o.correctionsHref || "/corrections/";
  const today = o.today || new Date().toISOString().slice(0, 10);
  const maxYear = +today.slice(0, 4) + 1;
  const okDate = (w) => w && +w.iso.slice(0, 4) >= 2020 && +w.iso.slice(0, 4) <= maxYear && w.iso <= today;

  const log = rowsOf(o.searched), cor = rowsOf(o.corrections);
  const entries = [];
  log.forEach((r, i) => {
    const w = parseWhen(first(r, F.when));
    const kind = outcomeOf(first(r, F.outcome), OUT);
    if (!okDate(w) || !kind) return;
    const ev = Array.isArray(r.ev) ? r.ev.find((e) => Array.isArray(e) && typeof e[0] === "string" && e[0].startsWith("/") && e[1]) : null;
    const place = String(first(r, F.place));
    const pages = String(first(r, F.pages));
    entries.push({
      iso: w.iso, exact: w.exact, kind, order: i,
      head: ev ? clean(ev[1]) : clip(first(r, F.what) || first(r, F.src), 120),
      more: ev ? clip(first(r, F.what), 240) : "",
      src: clip(first(r, F.src), 110),
      href: ev ? ev[0] : logHref,
      walked: r.walked === true,
      place: place.length > 0 && place.length <= 32 && !/[·;]/.test(place) ? place.trim() : "",
      pages: pages.length > 0 && pages.length <= 24 ? pages.trim() : "",
    });
  });
  cor.forEach((r, i) => {
    const w = parseWhen(first(r, F.cwhen));
    const what = first(r, F.cwhat);
    if (!okDate(w) || !what) return;
    entries.push({ iso: w.iso, exact: w.exact, kind: "corrected", order: 100000 + i, head: clip(what, 160), more: "", src: "", href: corHref, walked: false, place: "", pages: "" });
  });
  /* newest first; within a day, the later row of the log first */
  entries.sort((a, b) => (a.iso < b.iso ? 1 : a.iso > b.iso ? -1 : b.order - a.order));

  /* THE DAYS: entries of one day (month-only entries share their month); corrections are cards of their own, the day's searches fold into one */
  const days = [];
  for (const e of entries) {
    const key = e.exact ? e.iso : e.iso.slice(0, 7);
    let d = days[days.length - 1];
    if (!d || d.key !== key) days.push((d = { key, iso: e.iso, exact: e.exact, corrections: [], research: [] }));
    (e.kind === "corrected" ? d.corrections : d.research).push(e);
  }
  const listOf = (a, max) => (a.length <= 1 ? a.join("") : a.length <= max ? a.slice(0, -1).join(", ") + " and " + a[a.length - 1] : a.slice(0, max).join(", ") + " and " + (a.length - max) + " more");
  for (const d of days) {
    const r = d.research;
    d.found = r.filter((e) => e.kind === "found").length;
    const places = [...new Set(r.map((e) => e.place).filter(Boolean))];
    d.summary = r.length ? `Research: ${r.length} ${r.length === 1 ? "search" : "searches"}${places.length ? " at " + listOf(places, 3) : ""}` : "";
    d.tally = r.length ? ` · ${d.found} of ${r.length} found something` : "";
  }
  /* the flat list of cards, newest first, as the header panel shows it */
  const cards = [];
  for (const d of days) {
    for (const c of d.corrections) cards.push({ type: "corrected", iso: d.iso, exact: d.exact, head: c.head, href: c.href });
    if (d.research.length) cards.push({ type: "research", iso: d.iso, exact: d.exact, head: d.summary + d.tally, href: "/whats-new/#d" + d.key });
  }
  const latest = entries.length ? entries[0].iso : "";
  const weekFrom = latest ? new Date(Date.parse(latest + "T00:00:00Z") - 6 * 864e5).toISOString().slice(0, 10) : "";
  const week = {}, total = {};
  for (const k of Object.keys(KIND)) { week[k] = 0; total[k] = 0; }
  for (const e of entries) { total[e.kind]++; if (e.iso >= weekFrom) week[e.kind]++; }

  const wl = rowsOf(o.worklist);
  const c = o.counts || {};
  return {
    entries, days, cards, latest, weekFrom, week, total,
    counts: {
      people: c.people || 0,
      sources: c.sources || 0,
      logged: log.length,
      walked: log.filter((r) => r.walked === true).length,
      corrections: cor.length,
      done: wl.filter((r) => r.state === "done").length,
      open: wl.filter((r) => r.state === "next" || r.state === "running").length,
    },
  };
}

export const fmtDay = (iso, exact = true) => {
  const d = new Date(iso + "T00:00:00Z");
  return exact
    ? d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    : d.toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
};
export const nf = (n) => n.toLocaleString("en-GB");

/* the numbers of the panel and of the top of /whats-new/: [figure, name, what it counts]; a number the archive has none of is not shown */
export const tiles = (pulse) => {
  const c = pulse.counts;
  return [
    [c.people, "people", "in the register"],
    [c.logged, "searches", "of registers and sources logged"],
    [c.walked, "books walked", "every entry of the book read"],
    [c.corrections, "corrections", "claims withdrawn or fixed, in the open"],
    [c.done, "tasks done", `${nf(c.open)} still open`],
    [c.sources, "sources", "named and described"],
  ].filter(([n]) => n > 0).map(([n, l, d]) => [nf(n), l, d]);
};
