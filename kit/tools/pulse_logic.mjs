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
    let p; try { p = lib.buildPulse({ searched: c.searched, corrections: c.corrections, outcomeMap: c.outcomeMap, today: TODAY }); } catch (e) { out.push(c.id); continue; }
    if (!c.want(p)) out.push(c.id);
  }
  if (TILES(lib) !== "searches,tasks done,sources") out.push("tiles-hide-zero");
  return out;
}
const real = await import(pathToFileURL(libPath).href);
const fails = await failing(real);
ok("the real library passes every case (" + (CASES.length + 1) + ")", fails.length === 0, fails.join(", "));
for (const c of CASES) ok("case " + c.id, !fails.includes(c.id));

/* the rules shown to bite: break one in a copy, and the case it guards must fail */
const src = fs.readFileSync(libPath, "utf8");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pulse-"));
const BREAK = [
  ["future-date", "&& w.iso <= today", ""],
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
