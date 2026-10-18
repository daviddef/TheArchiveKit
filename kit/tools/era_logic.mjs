// node kit/tools/era_logic.mjs : the "at the time" note's library (lib/era.js) held to the shared cases (kit/data/era-cases.json),
// the markup the component draws (components/EraNote.astro) held to what the gate reads, and the gate (checkera.py) shown to accept
// what the library draws and to fail when the page is changed. The Python half of the library (eralib.py) is held to the SAME cases
// by era_selftest.py, so the two cannot drift apart.
import fs from "fs"; import os from "os"; import path from "path"; import { fileURLToPath, pathToFileURL } from "url";
import { spawnSync } from "child_process";
import * as E from "../lib/era.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const FIX = JSON.parse(fs.readFileSync(path.join(kit, "data", "era-cases.json"), "utf8"));
let bad = 0, n = 0;
const ok = (label, cond, detail) => { n++; if (!cond) { bad++; console.log("  FAIL  " + label + (detail ? "\n         " + detail : "")); } else console.log("  ok    " + label); };
const sub = (got, want) => Object.entries(want).every(([k, v]) => got != null && got[k] === v);
const snapFor = (c) => c.snap === "none" ? null : c.snap ? FIX.other_snapshots[c.snap] : FIX.snapshot;

/* the cases, run against a library (the real one, or a copy with one rule broken) -> the ids of the cases that fail */
function failing(lib) {
  const out = [];
  for (const c of FIX.cases) {
    const snap = JSON.parse(JSON.stringify(snapFor(c)));
    let got, why, threw = null;
    try { got = lib.eraAt(snap, c.place, c.year); why = lib.whyNot(snap, c.place, c.year); } catch (e) { threw = e.message; }
    const pass = threw === null && why === c.why && (c.want === null ? got === null : sub(got, c.want));
    if (!pass) out.push(c.id);
  }
  for (const [s, want] of FIX.fold) { let g; try { g = lib.fold(s); } catch (e) { g = "threw"; } if (g !== want) out.push("fold:" + s); }
  for (const [d, y, want] of FIX.years) { let g; try { g = lib.plainYear(d, y); } catch (e) { g = "threw"; } if (g !== want) out.push("year:" + d + "|" + y); }
  for (const h of FIX.href_cases) {
    const snap = { atlas: { base: h.base } }; let g; try { g = lib.regionHref(snap, "ruritania"); } catch (e) { g = "threw"; }
    if (g !== h.href) out.push(h.id);
  }
  // the words a reader gets
  const era = lib.eraAt(JSON.parse(JSON.stringify(FIX.snapshot)), "Hentzau", 1750);
  const html = lib.renderEra(era);
  if (!(html.startsWith('<span class="era-note" data-era="ruritania--1700" data-era-year="1750">') && html.includes('<span class="era-lab">Kingdom of Ruritania</span>')
        && html.includes('<a class="era-src" href="https://atlas.example.test/region/ruritania/" rel="noopener">per the Record Atlas</a>'))) out.push("render:note");
  if (lib.renderEra(null) !== "") out.push("render:null-is-empty");
  const seeded = lib.eraAt(JSON.parse(JSON.stringify(FIX.snapshot)), "Zenda", 1975);
  if (!lib.renderEra(seeded).includes("per this archive's own research</a>")) out.push("render:seeded-words");
  const e = lib.renderEra({ id: 'x--1"', label: "<script>alert(1)</script> & \"q\"", year: 1750, source: "<b>", href: 'https://a.example.test/"x' });
  if (/<script|<b>|\sx=|href="https:\/\/a\.example\.test\/"x/.test(e) || !e.includes("&lt;script&gt;") || !e.includes("&amp;") || !e.includes("&quot;")) out.push("render:escapes");
  return out;
}

const real = failing(E);
ok("the shared cases all hold (" + (FIX.cases.length + FIX.fold.length + FIX.years.length + FIX.href_cases.length) + " cases and the markup checks)", real.length === 0, real.join(", "));

// planted faults: a copy of era.js with one rule broken must fail the case that guards it
const src = fs.readFileSync(path.join(kit, "lib", "era.js"), "utf8");
const faults = [
  ["a boundary year gets a note", "const inside = touching.filter((e) => e.from < year && year < e.to);", "const inside = touching.filter((e) => e.from <= year && year <= e.to);", "first-year-of-an-era-is-a-boundary",
    [["x.from < year && year < x.to", "x.from <= year && year <= x.to"]]],
  ["an approximate era gets a note", "if (e.approx !== false && e.approx !== undefined) return \"approx\";", "", "an-approximate-era-is-silent"],
  ["an era flagged contested gets a note", "touching.some((e) => e.contested === true || overlapped(e))", "touching.some((e) => overlapped(e))", "an-era-marked-contested-is-silent",
    [["if (e.contested !== false && e.contested !== undefined) return \"contested\";", ""]]],
  ["an era that overlaps another is not contested", "touching.some((e) => e.contested === true || overlapped(e))", "touching.some((e) => e.contested === true)", "an-era-that-overlaps-another-is-silent-even-where-it-stands-alone"],
  ["a year inside two eras gets a note", "if (inside.length > 1 || touching.some((e) => e.contested === true || overlapped(e))) return \"contested\";", "", "a-year-inside-two-overlapping-eras-is-silent"],
  ["an empty regime label is allowed", "if (!label(snap, e)) return \"no-label\";", "", "an-empty-regime-label-is-silent"],
  ["a place is not folded for case", ".toLowerCase().replace(/['’`]/g, \"\")", ".replace(/['’`]/g, \"\")", "accents-and-case-are-folded"],
  ["a place is not folded for accents", ".normalize(\"NFKD\").replace(/[̀-ͯ]/g, \"\")", "", "accents-and-case-are-folded"],
  ["a string year is accepted", "Number.isInteger(n) && n >= 1 && n <= 9999", "Number(n) >= 1", "a-string-year-is-refused"],
  ["a fractional year is accepted", "Number.isInteger(n) && n >= 1 && n <= 9999", "n >= 1 && n <= 9999", "a-fractional-year-is-refused"],
  ["a words-only end year is an era", "isYear(e.from) && isYear(e.to) && e.from < e.to", "isYear(e.from) && e.from < e.to", "an-era-with-a-words-only-end-is-not-an-era"],
  ["an uncertain date has a year", "const m = PLAIN.exec(s) || ISO.exec(s);", "const m = /(\\d{4})/.exec(s);", "year:c. 1860|1860"],
  ["a date and a year need not agree", "if (!m || Number(m[1]) !== year) return null;", "if (!m) return null;", "year:1860|1861"],
  ["a snapshot of another version is read", "snap.version !== VERSION", "false", "a-snapshot-of-another-version-is-refused"],
  ["an http base is accepted", "/^https:\\/\\/[^/?#\\s]+$/i", "/^https?:\\/\\/[^/?#\\s]+$/i", "href-needs-https"],
  ["a seeded region is not marked", "const seeded = e.seeded_from_archive === true;", "const seeded = false;", "a-seeded-region-says-so"],
  ["a refused era is reported as no era", "const refused = (snap.dropped || []).some(", "const refused = false && (snap.dropped || []).some(", "a-refused-era-is-silent-and-counted-as-refused"],
  ["the label is not escaped", "const esc = (s) => String(s).replace(/&/g, \"&amp;\").replace(/</g, \"&lt;\").replace(/>/g, \"&gt;\").replace(/\"/g, \"&quot;\");", "const esc = (s) => String(s);", "render:escapes"],
  ["the year is not carried", " data-era-year=\"${esc(era.year)}\"", "", "render:note"],
  ["the source is not a link", "era.href\n    ? `<a class=\"era-src\"", "false\n    ? `<a class=\"era-src\"", "render:note"],
];
for (const [label, from, to, must, extra] of faults) {
  if (!src.includes(from)) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; }
  let broken = src.replace(from, to);
  let cannot = false;
  for (const [a, b] of (extra || [])) { if (!broken.includes(a)) cannot = true; broken = broken.replace(a, b); }
  if (cannot) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; }
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "era-fault-")); const f = path.join(d, "era.mjs");
  fs.writeFileSync(f, broken);
  let failed;
  try { failed = failing(await import(pathToFileURL(f).href)); } catch (e) { failed = ["threw: " + e.message]; }
  n++; if (failed.includes(must)) console.log("  ok    planted fault '" + label + "' is caught (" + must + ")"); else { bad++; console.log("  FAIL  planted fault '" + label + "' was NOT caught (failed: " + failed.join(", ") + ")"); }
  fs.rmSync(d, { recursive: true, force: true });
}

// the component draws what the library describes: its template carries the attributes the gate relies on
const astro = fs.readFileSync(path.join(kit, "components", "EraNote.astro"), "utf8");
for (const needle of ['class="era-note"', "data-era={note.id}", "data-era-year={note.year}", 'class="era-pre"', 'class="era-lab"', 'class="era-src"', 'rel="noopener"', "note.href", "era && era.id && era.label ? era : null"]) {
  ok("EraNote.astro carries " + needle, astro.includes(needle));
}
const astroCode = astro.replace(/\/\*[\s\S]*?\*\//g, "");
ok("EraNote.astro imports nothing of an archive's", !/from\s+["'](?!\.\.\/lib\/era\.js)/.test(astroCode));
ok("EraNote.astro draws no image", !/<img|<svg|background-image|flag/i.test(astroCode));

// the gate reads what the library draws, and fails when the page is changed
const t = fs.mkdtempSync(path.join(os.tmpdir(), "era-gate-"));
const snapPath = path.join(t, "era-snapshot.json");
fs.writeFileSync(snapPath, JSON.stringify(FIX.gate_snapshot));
const page = (body, head = "") => `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>A page</title>${head}</head><body><main><h1>A person</h1><div class="rec"><div class="v">Hentzau${body}</div></div></main></body></html>`;
const note = (p, y) => E.renderEra(E.eraAt(FIX.gate_snapshot, p, y));
const gate = (html, extra = []) => {
  const dist = path.join(t, "dist"); fs.rmSync(dist, { recursive: true, force: true });
  fs.mkdirSync(path.join(dist, "people", "a"), { recursive: true });
  fs.writeFileSync(path.join(dist, "people", "a", "index.html"), html);
  const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => k !== "ARCHIVE_OUT"));
  const r = spawnSync("python3", [path.join(here, "checkera.py"), "--dist", dist, "--snapshot", snapPath, ...extra], { encoding: "utf8", env });
  return { code: r.status, out: (r.stdout || "") + (r.stderr || "") };
};
const good = gate(page(note("Hentzau", 1750)));
ok("gate: a note the library drew is accepted (exit 0)", good.code === 0, good.out);
ok("gate: the page's own markup is what it reads (1 note, 1 page)", /1 page\(s\) read, 1 with a note, 1 note\(s\)/.test(good.out), good.out);
const wrongYear = gate(page(note("Hentzau", 1750).replace('data-era-year="1750"', 'data-era-year="1800"')));
ok("gate: the same note with a boundary year fails (year)", wrongYear.code === 1 && /year 1/.test(wrongYear.out), wrongYear.out);
const wrongWords = gate(page(note("Hentzau", 1750).replace("Kingdom of Ruritania", "Empire of Ruritania")));
ok("gate: the same note with other words fails (label)", wrongWords.code === 1 && /label 1/.test(wrongWords.out), wrongWords.out);
const living = gate(page(note("Hentzau", 1750), '<meta name="robots" content="noindex,nofollow">'));
ok("gate: a note on a noindex page fails", living.code === 1 && /noindex 1/.test(living.out), living.out);
const none = gate(page(""));
ok("gate: a site with no note at all is not a pass (exit 2)", none.code === 2, none.out);
fs.rmSync(t, { recursive: true, force: true });

console.log(bad ? "\n" + bad + " of " + n + " FAILED" : "\n  ok    " + n + " checks: the era note, its markup, and the gate that reads it");
process.exit(bad ? 1 : 0);
