// node kit/tools/rec_logic.mjs : the record link (components/Rec.astro) held to the shared cases (kit/data/rec-cases.json),
// and the gate (checkstandard.py) shown to read what it draws as a record link.
import fs from "fs"; import os from "os"; import path from "path"; import { fileURLToPath, pathToFileURL } from "url";
import { spawnSync } from "child_process";
import * as R from "../lib/rec.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const FIX = JSON.parse(fs.readFileSync(path.join(kit, "data", "rec-cases.json"), "utf8"));
let bad = 0, n = 0;
const ok = (label, cond, detail) => { n++; if (!cond) { bad++; console.log("  FAIL  " + label + (detail ? "\n         " + detail : "")); } else console.log("  ok    " + label); };
const sub = (got, want) => Object.entries(want).every(([k, v]) => (v && typeof v === "object") ? got[k] && sub(got[k], v) : (v === null ? got[k] === null : got[k] === v));

/* the cases, run against a library (the real one, or a copy with one rule broken) -> the ids of the cases that fail */
function failing(lib) {
  const out = [];
  let ix;
  try { ix = lib.index(FIX.records); } catch (e) { return FIX.cases.map((c) => c.id).concat(FIX.bad_tables.map((b) => "table:" + b.id), ["the fixture table was refused: " + e.message]); }
  for (const c of FIX.cases) {
    const opts = Object.assign({}, c.opts || {});
    if (typeof opts.root === "string") { const b = opts.root; opts.root = (p) => b + p; }
    let got, threw = null;
    try { got = lib.describe(ix, c.props, opts); } catch (e) { threw = e.message; }
    const pass = c.want.throws ? (threw !== null && threw.includes(c.want.throws)) : (threw === null && sub(got, c.want));
    if (!pass) out.push(c.id);
  }
  for (const b of FIX.bad_tables) {
    let threw = null;
    try { lib.index(JSON.parse(JSON.stringify(b.rows))); } catch (e) { threw = e.message; }
    if (!(threw !== null && threw.includes(b.throws))) out.push("table:" + b.id);
  }
  for (const g of FIX.ok_tables) {
    try { lib.index(JSON.parse(JSON.stringify(g.rows))); } catch (e) { out.push("table:" + g.id); }
  }
  // what is drawn
  const rr = (props, opts, text) => lib.renderRec(lib.describe(lib.index(FIX.records), props, opts || {}), text);
  const html = rr({ id: "deed-14" }, {}, "act 14 of 1898");
  if (!(html.includes('class="lk-rec"') && html.includes('data-rec="deed-14"') && /\sdata-cite[\s>]/.test(html) && html.includes('href="https://archive.example.test/ark:/1/14"')
        && html.includes('rel="noopener"') && html.includes(">act 14 of 1898</a>"))) out.push("render:link");
  if (rr({ id: "deed-13" }, {}, "x").includes("rel=")) out.push("render:internal-link-has-no-rel");
  if (rr({ id: "alive-1" }, { thumb: true }, "the living person's act") !== "") out.push("render:blocked-is-empty");
  if (rr({ id: "deed-13" }, {}, "") .indexOf(">The deed of 1898, act 13</a>") < 0) out.push("render:label-when-no-text");
  const e = rr({ id: "esc-1" }, {}, "<script>alert(1)</script> & \"q\"");
  if (/<script|<b>|"Q"|\sc="/.test(e) || !e.includes("&lt;script&gt;") || !e.includes("&amp;") || !e.includes("&quot;")) out.push("render:escapes");
  const fig = rr({ id: "deed-12" }, { thumb: true }, "act 12");
  if (!(fig.startsWith('<figure class="rec-fig" id="plate-1898-act12">') && fig.includes('<img src="/plates/1898-act12.jpg"') && fig.includes("<figcaption><a class=\"lk-rec\"")
        && fig.includes('width="640"') && fig.includes('loading="lazy"'))) out.push("render:figure");
  if (rr({ id: "deed-12" }, { thumb: true }, "x") .includes("alive")) out.push("render:no-leak");
  // one figure id per page
  const sc = {}, sc2 = {};
  if (!(lib.claim(sc, "plate-x") === true && lib.claim(sc, "plate-x") === false && lib.claim(sc2, "plate-x") === true)) out.push("claim");
  return out;
}

const real = failing(R);
ok("the shared cases all hold (" + (FIX.cases.length + FIX.bad_tables.length + FIX.ok_tables.length) + " cases and the markup checks)", real.length === 0, real.join(", "));

// planted faults: a copy of rec.js with one rule broken must fail the cases that guard it
const src = fs.readFileSync(path.join(kit, "lib", "rec.js"), "utf8");
const faults = [
  ["a living or held record is drawn", "return !!row && (truthy(row.living) || truthy(row.hold));", "return false;", "living-by-id-draws-nothing"],
  ["only living is honoured, not hold", "(truthy(row.living) || truthy(row.hold))", "(truthy(row.living))", "hold-draws-nothing-whatever-show-says"],
  ["a flag is only believed if it is exactly true", "const truthy = (v) => v === true || (v != null && v !== false && v !== 0 && v !== \"\" && v !== \"0\" && String(v).toLowerCase() !== \"false\");", "const truthy = (v) => v === true;", "a-string-flag-with-no-url-blocks-too"],
  ["show need not be exactly true", "row.show === true", "row.show", "show-must-be-exactly-true"],
  ["a thumbnail is drawn without being asked for", "if (thumb && row.show === true", "if (row.show === true", "no-thumb-unless-asked"],
  ["a living record's plate is still drawn", "if (isBlocked(row)) return { state: \"blocked\" };", "", "living-by-id-draws-nothing"],
  ["an unsafe scheme is accepted", "if (/^https?:\\/\\/[^/?#\\s]+/i.test(s)) return s;", "return s;", "table:unsafe-scheme"],
  ["a protocol-relative address is accepted", "if (s.startsWith(\"/\") && !s.startsWith(\"//\") && !s.includes(\"\\\\\")) return s;", "if (s.startsWith(\"/\")) return s;", "table:protocol-relative"],
  ["a plate may climb out of the plates folder", "&& !p.split(\"/\").some((seg) => seg === \"..\" || seg === \".\")", "", "table:plate-traversal", [["const PLATE = /^[\\p{L}\\p{N}_][\\p{L}\\p{N}_.\\- ]*", "const PLATE = /^[\\p{L}\\p{N}_.][\\p{L}\\p{N}_.\\- ]*"]]],
  ["an unknown record is silently dropped", "throw new RecError(`<Rec ${id != null", "return { state: \"plain\" }; throw new RecError(`<Rec ${id != null", "unknown-id-stops-the-build"],
  ["soft does nothing", "if (soft) return { state: \"plain\" };", "", "unknown-with-soft-is-plain-text"],
  ["id and locator together are allowed", "if ((id == null) === (act == null))", "if (id == null && act == null)", "both-id-and-locator"],
  ["a locator is not folded", "ix.byKey.get(fold(act))", "ix.byKey.get(String(act))", "locator-folds-punctuation"],
  ["a key is not folded when indexed", "const f = fold(k);", "const f = String(k);", "by-locator"],
  ["two records may share a key", "if (byKey.has(f) && byKey.get(f) !== r) throw", "if (false) throw", "table:shared-key"],
  ["a duplicate id is accepted", "if (byId.has(r.id)) throw", "if (false) throw", "table:duplicate-id"],
  ["the deployment base is not applied", "href.startsWith(\"/\") ? root(href) : href", "href", "root-relative-address-is-mapped"],
  ["the link text is not escaped", "const t = esc(text);", "const t = String(text);", "render:escapes"],
  ["an attribute is not escaped", "href=\"${esc(d.href)}\"", "href=\"${d.href}\"", "render:escapes", [["title=\"${esc(d.label)}\"", "title=\"${d.label}\""]]],
  ["the gate's mark is missing", " data-cite${d.kind", "${d.kind", "render:link"],
  ["an external link has no rel", "${d.external ? ' rel=\"noopener\"' : \"\"}", "", "render:link"],
  ["a blocked record is drawn as a link", "if (d.state === \"blocked\") return \"\";", "", "render:blocked-is-empty"],
  ["every duplicate figure keeps its id", "if (s.has(anchor)) return false;", "", "claim"],
];
for (const [label, from, to, must, extra] of faults) {
  if (!src.includes(from)) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; }
  let broken = src.replace(from, to);
  let cannot = false;
  for (const [a, b] of (extra || [])) { if (!broken.includes(a)) cannot = true; broken = broken.replace(a, b); }
  if (cannot) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; }
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "rec-fault-")); const f = path.join(d, "rec.mjs");
  fs.writeFileSync(f, broken);
  const M = await import(pathToFileURL(f).href);
  const failed = failing(M);
  n++; if (failed.includes(must)) console.log("  ok    planted fault '" + label + "' is caught (" + must + ")"); else { bad++; console.log("  FAIL  planted fault '" + label + "' was NOT caught (failed: " + failed.join(", ") + ")"); }
  fs.rmSync(d, { recursive: true, force: true });
}

// the component draws what the library describes: its template carries the attributes the gate and the tests rely on
const astro = fs.readFileSync(path.join(kit, "components", "Rec.astro"), "utf8");
for (const needle of ['class="lk-rec"', "data-rec={d.id}", "data-cite", 'class="rec-fig"', "describe(index(records)", "d.state === \"blocked\" ? null", "claim(Astro.request"]) {
  ok("Rec.astro carries " + needle, astro.includes(needle));
}
ok("Rec.astro imports nothing of an archive's", !/from\s+["'](?!\.\.\/lib\/(url|rec)\.js)/.test(astro));

// the gate reads a Rec link as a record link, with no host or prefix configured for it
const FX = path.join(kit, "data", "standard-fixtures");
const t = fs.mkdtempSync(path.join(os.tmpdir(), "rec-gate-"));
const dist = path.join(t, "dist");
fs.cpSync(path.join(FX, "site"), dist, { recursive: true });
const ix = R.index([
  { id: "far", url: "https://elsewhere.example.org/records/12", label: "Act 12", kind: "act", key: "12/1898" },
  { id: "plated", url: "https://elsewhere.example.org/records/9", label: "Act 9", kind: "act", plate: "1901-act9.jpg", show: true, key: "9/1901" },
  { id: "withheld", url: "https://elsewhere.example.org/records/7", label: "Act 7", plate: "1899-act7.jpg", show: true, living: true },
]);
const rec = (props, opts, text) => R.renderRec(R.describe(ix, props, opts), text);
const story = (body) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>The story</title></head><body><main><h1>The story</h1>`
  + `<section id="one"><h2>Part one</h2>${body}</section></main></body></html>`;
const run = (body) => {
  fs.mkdirSync(path.join(dist, "story"), { recursive: true });
  fs.writeFileSync(path.join(dist, "story", "index.html"), story(body));
  const r = spawnSync("python3", [path.join(here, "checkstandard.py"), "--dist", dist, "--index", path.join(FX, "index.json"), "--config", path.join(FX, "standard.json"),
    "--living", path.join(FX, "living.json"), "--floor", path.join(t, "none.json"), "--table"], { encoding: "utf8", env: Object.fromEntries(Object.entries(process.env).filter(([k]) => k !== "ARCHIVE_OUT")) });
  const m = (r.stdout || "").match(/^\s+\/story\/\s+L1 (\d+)\s+L2 (\d+)\s+L3 (\d+)\s+L4 (\d+)\s+L5 (\d+)\s+EX (\d+)/m);
  return m ? { L3: +m[3], L4: +m[4], out: r.stdout } : { out: (r.stdout || "") + (r.stderr || "") };
};
const plain = run(`<p>Act 12 of 1898 says so, at <a href="https://elsewhere.example.org/records/12">the record</a>.</p>`);
ok("gate control: a plain link to a host the config does not allow is not a record link (L3 1)", plain.L3 === 1, plain.out);
const withRec = run(`<p>${rec({ act: "12/1898" }, {}, "Act 12 of 1898")} says so.</p><p>Act 12 of 1898 again.</p>`);
ok("gate: a <Rec> link is a record link (L3 counts only the passage with none: 1 of 2)", withRec.L3 === 1, withRec.out);
const noDup = run(`<p>${rec({ id: "far" }, {}, "Act 12 of 1898")} says so.</p>`);
ok("gate: the passage with a <Rec> link counts 0", noDup.L3 === 0, noDup.out);
const linkOnly = run(`<p>${rec({ id: "plated" }, {}, "Act 9 of 1901")} says so.</p>`);
ok("gate: link-only where the scan is held but no thumbnail is placed: L3 0, L4 1 (the scan is not in the section)", linkOnly.L3 === 0 && linkOnly.L4 === 1, linkOnly.out);
const thumbed = run(`<p>Act 9 of 1901 says so.</p>${rec({ id: "plated" }, { thumb: true }, "Act 9 of 1901")}`);
ok("gate: the figure in place carries both: its caption link covers L3 (next block) and its image is the scan L4 asks for", thumbed.L3 === 0 && thumbed.L4 === 0, thumbed.out);
const nothing = rec({ id: "withheld" }, { thumb: true }, "Act 7 of 1899");
ok("a living record's <Rec> is the empty string in the page", nothing === "" && !story(`<p>${nothing}</p>`).includes("withheld") && !story(`<p>${nothing}</p>`).includes("1899-act7"));
fs.rmSync(t, { recursive: true, force: true });

console.log(bad ? "\n" + bad + " of " + n + " FAILED" : "\n  ok    " + n + " checks: the record link and the gate that reads it");
process.exit(bad ? 1 : 0);
