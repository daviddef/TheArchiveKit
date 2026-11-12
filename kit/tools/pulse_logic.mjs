// node kit/tools/pulse_logic.mjs : the pulse (lib/pulse.js, behind the ribbon and /whats-new/) held to cases written from the real shapes the
// eight archives keep their logs in (ISO dates, long month names, undated record years, a leading _note row, status for outcome), and the
// rules shown to bite: a copy of the library with one rule broken must fail the case that rule exists for.
import fs from "fs"; import os from "os"; import path from "path"; import { fileURLToPath, pathToFileURL } from "url";
const here = path.dirname(fileURLToPath(import.meta.url));
const libPath = path.join(here, "..", "lib", "pulse.js");
let bad = 0, n = 0;
const ok = (label, cond, detail) => { n++; if (!cond) { bad++; console.log("  FAIL  " + label + (detail ? "\n         " + detail : "")); } else console.log("  ok    " + label); };

const TODAY = "2026-11-11";
/* each case: the archive's rows, and what the pulse must show; `id` names the rule it guards */
const CASES = [
  { id: "iso-and-note", searched: [{ _note: "a note to the reader" }, { src: "A", what: "baptisms", when: "2026-11-10", outcome: "yield" }, { src: "B", what: "burials", when: "2026-11-10", outcome: "nothing" }],
    want: (p) => p.entries.length === 2 && p.days.length === 1 && p.days[0].research.length === 2 && p.days[0].found === 1 && p.counts.logged === 2 },
  { id: "long-month", searched: [{ src: "A", what: "x", when: "27 September 2026", outcome: "yield" }, { src: "A", what: "y", when: "Sept 2026", outcome: "partial" }],
    want: (p) => p.entries.length === 2 && p.days.length === 2 && p.days[0].exact === true && p.days[1].exact === false },
  { id: "record-year-is-not-a-date", searched: [{ when: "1814", what: "a record year", outcome: "found" }, { when: "2024", what: "a bare year", outcome: "found" }, { when: "Arienzo 1890–1900: the printed tavolae", what: "x", outcome: "found" }],
    want: (p) => p.entries.length === 0 && p.days.length === 0 },
  { id: "future-date", searched: [{ when: "2027-03-01", what: "typo", outcome: "yield" }], want: (p) => p.entries.length === 0 },
  /* a work date is the researcher's LOCAL day; the build day (`today`) is UTC. One day ahead is real (Australia is UTC+10/11), two is a typo (12 Nov 2026) */
  { id: "today-kept", searched: [{ when: "2026-11-11", what: "x", outcome: "yield" }], want: (p) => p.entries.length === 1 && p.latest === "2026-11-11" },
  { id: "one-day-ahead-kept", searched: [{ when: "2026-11-12", what: "x", outcome: "yield" }, { when: "12 Nov 2026", what: "y", outcome: "nothing" }],
    want: (p) => p.entries.length === 2 && p.latest === "2026-11-12" && p.days.length === 1 && p.days[0].iso === "2026-11-12" },
  { id: "two-days-ahead-dropped", searched: [{ when: "2026-11-13", what: "x", outcome: "yield" }, { when: "13 Nov 2026", what: "y", outcome: "yield" }],
    want: (p) => p.entries.length === 0 && p.latest === "" },
  { id: "invalid-date-dropped", searched: [{ when: "2026-13-01", what: "month 13", outcome: "yield" }, { when: "tomorrow", what: "a word", outcome: "yield" }, { when: "", what: "empty", outcome: "yield" }, { what: "no date", outcome: "yield" }, { when: "32 Nov 2026", what: "day 32", outcome: "yield" }],
    want: (p) => p.entries.length === 0 && p.counts.logged === 5 },
  { id: "corrections-one-day-ahead", searched: [], corrections: [{ date: "2026-11-12", what: "ahead by one" }, { date: "2026-11-13", what: "ahead by two" }, { date: "2026-11-11", what: "today" }],
    want: (p) => p.entries.length === 2 && !p.entries.some((e) => e.iso === "2026-11-13") && p.days[0].iso === "2026-11-12" && p.days[0].corrections.length === 1 },
  /* the seven days count back from `latest` (the newest work date), so a row a day ahead is the newest day and is in the week */
  { id: "week-window-with-day-ahead", searched: [{ when: "2026-11-12", what: "a", outcome: "yield" }, { when: "2026-11-06", what: "b", outcome: "yield" }, { when: "2026-11-05", what: "c", outcome: "yield" }, { when: "2026-11-12", what: "d", outcome: "nothing" }],
    want: (p) => p.latest === "2026-11-12" && p.weekFrom === "2026-11-06" && p.week.found === 2 && p.week.nil === 1 && p.total.found === 3 },
  /* o.today overrides the build day, and the day after it is computed across month, year and leap-day ends */
  { id: "today-override", today: "2026-11-30", searched: [{ when: "2026-12-01", what: "next month, one day ahead", outcome: "yield" }, { when: "2026-12-02", what: "two ahead", outcome: "yield" }, { when: "2026-11-11", what: "past", outcome: "yield" }],
    want: (p) => p.entries.length === 2 && p.latest === "2026-12-01" },
  { id: "today-override-year-end", today: "2026-12-31", searched: [{ when: "2027-01-01", what: "new year, one day ahead", outcome: "yield" }, { when: "2027-01-02", what: "two ahead", outcome: "yield" }],
    want: (p) => p.entries.length === 1 && p.latest === "2027-01-01" },
  { id: "today-override-leap-day", today: "2028-02-28", searched: [{ when: "2028-02-29", what: "leap day", outcome: "yield" }, { when: "2028-03-01", what: "two ahead", outcome: "yield" }],
    want: (p) => p.entries.length === 1 && p.latest === "2028-02-29" },
  { id: "status-for-outcome", searched: [{ when: "2026-11-01", scope: "a scope", status: "found" }, { when: "2026-11-01", scope: "b", outcome: "no Falco" }, { when: "2026-11-01", scope: "c", status: "outstanding" }],
    want: (p) => p.entries.length === 2 && p.entries.filter((e) => e.kind === "nil").length === 1 },
  { id: "corrections-by-date", searched: [], corrections: { rows: [{ date: "2026-11-09", what_was_said: "a claim withdrawn" }, { what: "undated" }] },
    want: (p) => p.entries.length === 1 && p.cards.length === 1 && p.cards[0].type === "corrected" && p.counts.corrections === 2 },
  { id: "source-name-link-group", searched: [
      { source: "Antenati — Linguaglossa, Nati 1887", scope: "annual index read", when: "2026-11-11", outcome: "done", status: "done", url: "https://antenati.cultura.gov.it/x", pages: "48-49" },
      { src: "Antenati — Nati 1888", what: "act 3", when: "2026-11-11", outcome: "nothing", href: "/searched/" },
      { src: "FamilySearch full text, Aguada", what: "burials", when: "2026-11-11", outcome: "nothing", urls: ["https://www.familysearch.org/ark:/61903/3:1:X"] }],
    outcomeMap: { done: "found" },
    want: (p) => { const d = p.days[0]; return d.groups.length === 2 && d.groups.find((g) => g.name === "Antenati").rows.length === 2
      && d.used === " — used FamilySearch full text and Antenati"
      && p.entries.find((e) => e.src.startsWith("Antenati — Ling")).ext === "https://antenati.cultura.gov.it/x"
      && p.entries.find((e) => e.src.startsWith("Antenati — Nati")).ext === ""
      && p.entries.find((e) => e.provider === "FamilySearch full text").ext.startsWith("https://www.familysearch.org/")
      && p.entries.find((e) => e.src.startsWith("Antenati — Ling")).title.startsWith("Antenati — Linguaglossa"); } },
  { id: "empty", searched: undefined, want: (p) => p.entries.length === 0 && p.days.length === 0 && p.latest === "" && p.cards.length === 0 },
];
const TILES = (lib) => lib.tiles({ counts: { people: 0, sources: 5, logged: 3, walked: 0, corrections: 0, done: 2, open: 1 } }).map((t) => t[1]).join(",");

async function failing(lib) {
  const out = [];
  for (const c of CASES) {
    let p; try { p = lib.buildPulse({ searched: c.searched, corrections: c.corrections, outcomeMap: c.outcomeMap, today: c.today || TODAY }); } catch (e) { out.push(c.id); continue; }
    if (!c.want(p)) out.push(c.id);
  }
  if (TILES(lib) !== "searches,tasks done,sources") out.push("tiles-hide-zero");
  return out;
}
const real = await import(pathToFileURL(libPath).href);
const fails = await failing(real);
ok("the real library passes every case (" + (CASES.length + 1) + ")", fails.length === 0, fails.join(", "));
for (const c of CASES) ok("case " + c.id, !fails.includes(c.id));

/* with no o.today the build day is now, in UTC: a row dated tomorrow-UTC is kept, one dated the day after that is not (this is the line the Falco rows hit) */
{
  const iso = (days) => new Date(Date.now() + days * 864e5).toISOString().slice(0, 10);
  const p = real.buildPulse({ searched: [{ when: iso(1), what: "a", outcome: "yield" }, { when: iso(2), what: "b", outcome: "yield" }, { when: iso(0), what: "c", outcome: "yield" }] });
  /* (a build that straddles 00:00 UTC while this runs could move the day by one; the dates were taken a moment before the build) */
  ok("no o.today: the UTC day, tomorrow and the day after (kept, kept, dropped)", p.entries.length === 2 && p.latest === iso(1), p.entries.length + " entries, latest " + p.latest);
}
ok("dayAfter: month, year and leap-day ends", real.dayAfter("2026-11-30") === "2026-12-01" && real.dayAfter("2026-12-31") === "2027-01-01" && real.dayAfter("2028-02-28") === "2028-02-29" && real.dayAfter("2026-02-28") === "2026-03-01");

/* the rules shown to bite: break one in a copy, and the case it guards must fail */
const src = fs.readFileSync(libPath, "utf8");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pulse-"));
/* pulse.js imports ./receipts.js (12 November 2026): the copies need it beside them, as an ES module */
fs.copyFileSync(path.join(here, "..", "lib", "receipts.js"), path.join(tmp, "receipts.js")); fs.writeFileSync(path.join(tmp, "package.json"), '{"type":"module"}');
const BREAK = [
  ["future-date", "&& w.iso <= tomorrow", ""],
  ["one-day-ahead-kept", "const tomorrow = dayAfter(today);", "const tomorrow = today;"],
  ["two-days-ahead-dropped", "const tomorrow = dayAfter(today);", "const tomorrow = dayAfter(dayAfter(today));"],
  ["today-override", "const today = o.today ||", "const today = "],
  ["record-year-is-not-a-date", "if (!m) return null;\n  const mo = MON", "if (!m) return { iso: t.slice(0,4)+'-01-01', exact: false };\n  const mo = MON"],
  ["iso-and-note", '!("_note" in r)', "true"],
  ["source-name-link-group", "/^https?:\\/\\//i.test(x.trim())", "true"],
  ["tiles-hide-zero", ".filter(([n]) => n > 0)", ""],
];
for (const [id, from, to] of BREAK) {
  if (!src.includes(from)) { ok("fault " + id + ": the line to break is still in the library", false, from); continue; }
  const f = path.join(tmp, id + ".mjs"); fs.writeFileSync(f, src.replace(from, to));
  const lib = await import(pathToFileURL(f).href);
  ok("fault " + id + ": the broken copy is caught", (await failing(lib)).includes(id));
}
fs.rmSync(tmp, { recursive: true, force: true });
console.log(bad ? `\n${bad} of ${n} FAILED` : `\npulse_logic: ${n} checks ok`);
process.exit(bad ? 1 : 0);
