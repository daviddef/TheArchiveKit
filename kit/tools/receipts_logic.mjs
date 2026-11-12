// node kit/tools/receipts_logic.mjs : the receipts (lib/receipts.js, lib/receipts.client.js, the Atlas/Updated fields of lib/pulse.js and the "found" rule
// of tools/check_row_pages.py) held to cases, and the rules shown to bite: a copy with one rule broken must fail the case that rule exists for.
//   1. rowkey: the spec's three test vectors, and Python's json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False) on more rows
//   2. stateOf: every state, and "cannot tell" when a file could not be read
//   3. loadReceipts: any failure is null and never throws; a hung fetch times out
//   4. the view-time script's copy of stateOf answers identically to lib/receipts.js, over a grid of receipts
//   5. buildPulse: key / atlas / updated on entries, the "N of M in the Atlas" tally, and "no receipts = as before"
//   6. check_row_pages.py reads dates and outcome words exactly as pulse.js does
import fs from "fs"; import os from "os"; import path from "path"; import { execFileSync } from "child_process"; import { fileURLToPath, pathToFileURL } from "url";
const here = path.dirname(fileURLToPath(import.meta.url));
const lib = path.join(here, "..", "lib");
let bad = 0, n = 0;
const ok = (label, cond, detail) => { n++; if (!cond) { bad++; console.log("  FAIL  " + label + (detail ? "\n         " + detail : "")); } else console.log("  ok    " + label); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const py = (code, input) => execFileSync("python3", ["-I", "-c", code], { input: JSON.stringify(input), encoding: "utf8" });

/* a throwaway copy of the library (receipts.js, pulse.js and the client) with one line changed, to see the case it guards fail */
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "receipts-"));
const copy = (name, edits) => {
  const d = path.join(tmp, name); fs.mkdirSync(d); fs.writeFileSync(path.join(d, "package.json"), '{"type":"module"}');
  for (const f of ["receipts.js", "pulse.js", "receipts.client.js"]) {
    let s = fs.readFileSync(path.join(lib, f), "utf8");
    for (const [from, to] of edits[f] || []) { if (!s.includes(from)) throw new Error("fault line not found in " + f + ": " + from); s = s.replace(from, to); }
    fs.writeFileSync(path.join(d, f), s);
  }
  return d;
};
const load = async (dir, f = "receipts.js") => import(pathToFileURL(path.join(dir, f)).href + "?" + Math.random());
const clientOf = (dir) => new Function(fs.readFileSync(path.join(dir, "receipts.client.js"), "utf8") + "\n;return wnReceipts;")();

/* ---- 1. rowkey ---- */
const VECTORS = [
  [{ when: "12 Nov 2026", src: "FamilySearch", what: "Gologorica baptisms 1872–1880", outcome: "hit" }, "e7c29e4b77d3"],
  [{ outcome: "nil", what: "Šestan «Žubrinić» — nothing", when: "2026-11-11", src: "DAPA ZM34K-214", pages: "p. 12", ev: [["/imotski/", "Imotski"]] }, "afb2db3a6e3a"],
  [{ key: "x-1", when: "10 Nov 2026", walked: true, n: 3, nested: { b: [1, 2], a: "é" } }, "7e662c5e1f2f"],
];
const EXTRA = [
  { a: null, b: [], c: {}, d: "tab\there", e: "quote\"s and \\ back", f: -3, g: 1e21 },
  { z: { y: { x: [{ w: 1, v: 2 }] } }, "ключ": "значение", "ö": "ü", emoji: "😀" },
  { when: "2026-11-12", ev: [["/a/", "A"], ["/b/#c", "B"]], logOnly: true, url: "https://x.example/a?b=c&d=é" },
];
const R = await import(pathToFileURL(path.join(lib, "receipts.js")).href);
for (const [row, want] of VECTORS) ok("rowkey vector " + want, R.rowkey(row) === want, R.rowkey(row));
const pyKeys = JSON.parse(py("import sys,json,hashlib\nrows=json.load(sys.stdin)\nprint(json.dumps([hashlib.sha1(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()[:12] for r in rows]))", [...VECTORS.map((v) => v[0]), ...EXTRA]));
ok("rowkey equals Python on " + pyKeys.length + " rows (vectors, non-ASCII, nested, null, escapes)", same(pyKeys, [...VECTORS.map((v) => v[0]), ...EXTRA].map(R.rowkey)), JSON.stringify(pyKeys));
ok("key order does not matter, an edited row changes its key", R.rowkey({ a: 1, b: 2 }) === R.rowkey({ b: 2, a: 1 }) && R.rowkey({ a: 1 }) !== R.rowkey({ a: 2 }));

/* ---- 2. stateOf ---- */
const file = (rows) => ({ v: 1, exported: "2026-11-12", rows });
const LIVE = file({ k1: [["volume:9R28-C6V", "/place/x/#a"], ["source:familysearch", "/source/fs/"]], k4: [] });
const MAIN = file({ k1: [["volume:9R28-C6V", "/place/x/#a"]], k2: [["volume:Q", "/place/y/"]], k5: [] });
const S = (k, l = LIVE, m = MAIN) => R.stateOf(k, l, m);
ok("in-atlas: in the deployed file, first href made absolute, all marks", S("k1").state === "in-atlas" && S("k1").href === "https://recordatlas.org/place/x/#a" && S("k1").marks.length === 2);
ok("going-live: in main, not deployed", S("k2").state === "going-live" && S("k2").href === "https://recordatlas.org/place/y/");
ok("not-sent: in neither, both files read", S("k3").state === "not-sent" && S("k3").href === "" && S("k3").marks.length === 0);
ok("nothing-to-send: an empty list in either file", S("k4").state === "nothing-to-send" && S("k5").state === "nothing-to-send");
ok("deployed wins over main", S("k1", LIVE, file({ k1: [] })).state === "in-atlas");
ok("cannot tell: a key in neither, one file unread -> null", S("k3", LIVE, null) === null && S("k3", null, MAIN) === null && S("k3", null, null) === null);
ok("a key found in the one file that was read still answers", S("k1", LIVE, null).state === "in-atlas" && S("k2", null, MAIN).state === "going-live");
ok("a bad receipt (no rows, rows as array, a string) is an unread file", S("k1", { v: 1 }, MAIN) === null || S("k1", { v: 1 }, MAIN).state !== "in-atlas");
ok("only Atlas paths become links (another host, //host, javascript: are dropped)", R.atlasHref("//evil.example/x") === "" && R.atlasHref("https://evil.example/x") === "" && R.atlasHref("javascript:alert(1)") === "" && R.atlasHref("/place/z/") === "https://recordatlas.org/place/z/");
ok("a mark with a foreign href is not a mark (the row reads as no mark)", R.stateOf("q", file({ q: [["volume:Z", "https://evil.example/"]] }), MAIN).state === "nothing-to-send");

/* ---- 3. loadReceipts ---- */
const resp = (body, okk = true) => ({ ok: okk, json: async () => body });
const urls = [];
const goodFetch = async (u) => { urls.push(u); return resp(u.startsWith("https://recordatlas.org/") ? LIVE : MAIN); };
const got = await R.loadReceipts("defranceschi", { fetch: goodFetch, now: "2026-11-12T10:00:00Z" });
ok("loadReceipts: live and main read from the two addresses, asOf is the day", got && got.live === LIVE && got.main === MAIN && got.asOf === "2026-11-12"
  && urls.includes("https://recordatlas.org/research-receipts/defranceschi.json") && urls.includes("https://raw.githubusercontent.com/daviddef/TheMap/main/site/public/research-receipts/defranceschi.json"), JSON.stringify(urls));
ok("loadReceipts: a fetch that throws -> null", (await R.loadReceipts("falco", { fetch: async () => { throw new Error("offline"); } })) === null);
ok("loadReceipts: HTTP 404/500 -> null", (await R.loadReceipts("falco", { fetch: async () => resp({}, false) })) === null);
ok("loadReceipts: bad JSON, a non-receipt, a future version -> null", (await R.loadReceipts("falco", { fetch: async () => ({ ok: true, json: async () => { throw new SyntaxError("x"); } }) })) === null
  && (await R.loadReceipts("falco", { fetch: async () => resp({ hello: 1 }) })) === null && (await R.loadReceipts("falco", { fetch: async () => resp({ v: 2, rows: {} }) })) === null);
const half = await R.loadReceipts("falco", { fetch: async (u) => (u.startsWith("https://recordatlas") ? resp({}, false) : resp(MAIN)) });
ok("loadReceipts: one file unread -> the other is kept, the unread is null", half && half.live === null && half.main === MAIN);
const t0 = Date.now();
ok("loadReceipts: a fetch that never answers (and ignores abort) times out", (await R.loadReceipts("falco", { fetch: () => new Promise(() => {}), timeout: 60 })) === null && Date.now() - t0 < 2000);
const warned = []; const w0 = console.warn; console.warn = (m) => warned.push(m);
ok("loadReceipts: only the Atlas's eight ids are read (Defranceski is defranceschi); anything else warns and is null, never a throw", (await R.loadReceipts("", { fetch: goodFetch })) === null && (await R.loadReceipts("../x", { fetch: goodFetch })) === null && (await R.loadReceipts(undefined)) === null
  && (await R.loadReceipts("defranceski", { fetch: goodFetch })) === null && warned.some((m) => m.includes("defranceski"))
  && R.ARCHIVE_IDS.join() === "blazevic,booyzen,darcy,defranceschi,falco,lerena,luwinski,mazza" && (await Promise.all(R.ARCHIVE_IDS.map((i) => R.loadReceipts(i, { fetch: goodFetch })))).every(Boolean));
console.warn = w0;

/* ---- 4. the script's copy answers like stateOf ---- */
const GRID_FILES = [null, { v: 1, rows: {} }, { rows: [] }, "x", file({ a: [], b: [["volume:1", "/p/1/"]], c: [["volume:2", "/p/2/"], ["source:s", "/s/"], ["bad", 5]], d: [["x", "https://evil.example/"]] }), file({ a: [["volume:1", "/p/9/"]], b: [], e: [["volume:3", "//host/x"]] }), file({ c: [] })];
const equivalence = (client) => {
  const diffs = [];
  for (const l of GRID_FILES) for (const m of GRID_FILES) for (const k of ["a", "b", "c", "d", "e", "zz", "__proto__", "constructor"]) {
    const x = R.stateOf(k, l, m), y = client.stateOf(k, l, m);
    if (!same(x, y)) diffs.push(`${k} ${JSON.stringify(l)?.slice(0, 40)} ${JSON.stringify(m)?.slice(0, 40)}: ${JSON.stringify(x)} vs ${JSON.stringify(y)}`);
  }
  return diffs;
};
const realClient = clientOf(lib);
const diffs = equivalence(realClient);
ok("view-time script: stateOf answers identically to lib/receipts.js over " + GRID_FILES.length ** 2 * 8 + " cases", diffs.length === 0, diffs.slice(0, 3).join("\n         "));
ok("view-time script: atlasHref identical", ["/a/", "//x", "https://recordatlas.org/q/", "https://evil.example/", "javascript:1", "", null, 5, " /sp/ ", "/has space/"].every((h) => realClient.atlasHref(h) === R.atlasHref(h)));
ok("view-time script does nothing, and does not throw, without a page", (() => { try { realClient.run(); return true; } catch (e) { return false; } })());

/* the page script when the Atlas cannot be reached (the CORS header is not deployed yet; offline; 404; bad JSON): it must change nothing and throw nothing */
{
  const bar = { hidden: true, text: "built", getAttribute: (a) => ({ "data-live": "https://recordatlas.org/x.json", "data-main": "https://raw.githubusercontent.com/x.json" })[a], setAttribute() { bar.fresh = true; }, querySelector: () => ({ set textContent(v) { bar.text = v; } }) };
  let touched = 0; const g = globalThis, saved = { document: g.document, fetch: g.fetch };
  g.document = { getElementById: () => bar, querySelectorAll: () => { touched++; return []; } };
  const modes = { "a network/CORS failure (fetch rejects)": async () => { throw new TypeError("Failed to fetch"); }, "HTTP 404": async () => resp({}, false), "not a receipt": async () => resp({ hello: 1 }), "invalid JSON": async () => ({ ok: true, json: async () => { throw new SyntaxError("x"); } }), "hangs forever": () => new Promise(() => {}) };
  let thrown = null; const rej = (e) => { thrown = e; }; process.on("unhandledRejection", rej);
  for (const [name, f] of Object.entries(modes)) {
    g.fetch = f; touched = 0; bar.hidden = true; bar.text = "built"; bar.fresh = false;
    const c = new Function(fs.readFileSync(path.join(lib, "receipts.client.js"), "utf8") + "\n;return wnReceipts;")(); // auto-runs with the stub document
    await new Promise((r) => setTimeout(r, name === "hangs forever" ? 50 : 30));
    ok("view-time script, " + name + ": nothing changes, nothing thrown", touched === 0 && bar.hidden === true && bar.text === "built" && !bar.fresh && thrown === null);
  }
  process.off("unhandledRejection", rej); g.document = saved.document; g.fetch = saved.fetch;
  if (saved.document === undefined) delete g.document;
}

/* ---- 5. buildPulse ---- */
const P = await import(pathToFileURL(path.join(lib, "pulse.js")).href);
const ROWS = [VECTORS[0][0], VECTORS[1][0],
  { when: "12 Nov 2026", src: "Archive Z", what: "third", outcome: "found", ev: [["/story/", "Story"], ["/story/", "again"], ["//evil/", "x"], ["/imotski/#a", "Imotski"]] },
  { when: "12 Nov 2026", src: "Archive Y", what: "fourth", outcome: "found", logOnly: true },
  { when: "12 Nov 2026", src: "Archive X", what: "fifth", outcome: "nothing" }];
const keys = ROWS.map(R.rowkey);
const rc = { asOf: "2026-11-12", live: file({ [keys[0]]: [["volume:A", "/place/a/"]], [keys[1]]: [] }), main: file({ [keys[0]]: [["volume:A", "/place/a/"]], [keys[2]]: [["volume:B", "/place/b/"]] }) };
const pr = P.buildPulse({ searched: ROWS, receipts: rc, today: "2026-11-12" });
const e0 = pr.entries.find((e) => e.key === keys[0]), e1 = pr.entries.find((e) => e.key === keys[1]), e2 = pr.entries.find((e) => e.key === keys[2]), e3 = pr.entries.find((e) => e.key === keys[3]), e4 = pr.entries.find((e) => e.key === keys[4]);
ok("entries carry the row key, and it is rowkey(row)", pr.entries.length === 5 && [e0, e1, e2, e3, e4].every(Boolean));
ok("entries carry atlas {state, href, marks}", e0.atlas.state === "in-atlas" && e0.atlas.href === "https://recordatlas.org/place/a/" && e1.atlas.state === "nothing-to-send" && e2.atlas.state === "going-live" && e3.atlas.state === "not-sent" && e4.atlas.state === "not-sent");
ok("updated: pages from ev (once each, site paths only), logOnly, or neither", same(e2.updated, { pages: [["/story/", "Story"], ["/imotski/#a", "Imotski"]], logOnly: false }) && same(e3.updated, { pages: [], logOnly: true }) && same(e4.updated, { pages: [], logOnly: false }) && same(e1.updated.pages, [["/imotski/", "Imotski"]]));
const d = pr.days.find((x) => x.iso === "2026-11-12"), d1 = pr.days.find((x) => x.iso === "2026-11-11");
ok("the day tally: 1 of 4 in the Atlas (nothing-to-send not counted; going-live and not-sent are)", d.atlas.in === 1 && d.atlas.going === 1 && d.atlas.notSent === 2 && d.atlas.makes === 4 && d.atlasTally === " · 1 of 4 in the Atlas", JSON.stringify(d.atlas) + d.atlasTally);
ok("a day with only nothing-to-send rows has no tally", d1.atlas.makes === 0 && d1.atlasTally === "" );
ok("pulse.atlas says when the snapshot was taken", same(pr.atlas, { asOf: "2026-11-12", live: true, main: true }));
const strip = (p) => JSON.parse(JSON.stringify(p, (k, v) => (k === "atlas" || k === "atlasTally" ? undefined : v)));
const plain = P.buildPulse({ searched: ROWS, today: "2026-11-12" });
ok("no receipts (absent, null, both files unread): no Atlas state anywhere, nothing else changes", plain.atlas === null && plain.entries.every((e) => e.atlas === null) && plain.days.every((x) => x.atlas === null && x.atlasTally === "")
  && same(strip(plain), strip(P.buildPulse({ searched: ROWS, receipts: null, today: "2026-11-12" }))) && same(strip(plain), strip(P.buildPulse({ searched: ROWS, receipts: { live: null, main: null }, today: "2026-11-12" }))));
ok("with receipts, everything else is as without", same(strip({ ...pr, entries: pr.entries.map((e) => ({ ...e, atlas: 0 })) }), strip({ ...plain, entries: plain.entries.map((e) => ({ ...e, atlas: 0 })) })) );
ok("corrections carry no key and no state", (() => { const c = P.buildPulse({ searched: [], corrections: [{ when: "2026-11-12", what: "w" }], receipts: rc, today: "2026-11-12" }).entries[0]; return c.key === "" && c.atlas === null && same(c.updated, { pages: [], logOnly: false }); })());

/* ---- 6. check_row_pages.py reads the log as pulse.js does ---- */
const WHENS = ["2026-11-11", "2026-11", "2026-13-01", "2026-11-11T09:00", "11 Nov 2026", "5 October 2026", "Sept 2026", "Sept. 2026", "1814", "2024", "Arienzo 1890–1900: the printed tavolae", "11 Foo 2026", "", "  3 Mar 2026 ", "2026-1-5"];
const WORDS = ["hit", "yield", "found", "Found ", "nothing", "nil", "miss", "clean", "null", "empty", "partial", "part", "mixed", "blocked", "correction", "no Falco", "not there", "nothing on it", "pending", "done", "outstanding", "", "No"];
const pyOut = JSON.parse(py("import sys,json\nsys.path.insert(0,%r)\nimport check_row_pages as c\nd=json.load(sys.stdin)\nprint(json.dumps({'w':[c.parse_when(w) for w in d['w']],'o':[c.outcome_of(w, d['m']) for w in d['o']],'o0':[c.outcome_of(w) for w in d['o']]}))".replace("%r", JSON.stringify(path.join(here))), { w: WHENS, o: WORDS, m: { done: "found" } }));
const jsWhen = WHENS.map((w) => { const r = P.parseWhen(w); return r ? [r.iso, r.exact] : null; });
ok("check_row_pages.parse_when equals pulse.js parseWhen on " + WHENS.length + " strings", same(pyOut.w, jsWhen), JSON.stringify(pyOut.w) + "\n" + JSON.stringify(jsWhen));
const jsKind = (m) => WORDS.map((w) => { const e = P.buildPulse({ searched: [{ when: "2026-11-01", outcome: w }], outcomeMap: m, today: "2026-11-12" }).entries[0]; return e ? e.kind : null; });
const kindOf = (k) => (k === "found" ? "found" : k ? "other" : null);
ok("check_row_pages.outcome_of equals pulse.js outcomeOf on " + WORDS.length + " words (found / other / left out), with and without an outcomeMap",
  same(pyOut.o0.map(kindOf), jsKind().map(kindOf)) && same(pyOut.o.map(kindOf), jsKind({ done: "found" }).map(kindOf)), JSON.stringify(pyOut.o0) + "\n" + JSON.stringify(jsKind()));

/* ---- the rules shown to bite ---- */
const FAULTS = [
  ["rowkey: keys not sorted", { "receipts.js": [['Object.keys(v).sort()', 'Object.keys(v)']] }, async (dir) => { const m = await load(dir); return !VECTORS.every(([r, k]) => m.rowkey(r) === k); }],
  ["rowkey: more than 12 hex", { "receipts.js": [['.slice(0, 12)', '.slice(0, 13)']] }, async (dir) => { const m = await load(dir); return !VECTORS.every(([r, k]) => m.rowkey(r) === k); }],
  ["stateOf: a missing file read as 'not sent'", { "receipts.js": [['if (L && M) return done("not-sent");', 'return done("not-sent");']] }, async (dir) => { const m = await load(dir); return m.stateOf("k3", LIVE, null) !== null; }],
  ["stateOf: main read before the deployed file", { "receipts.js": [['if (L && has(L, key)) {', 'if (false) {']] }, async (dir) => { const m = await load(dir); return m.stateOf("k1", LIVE, MAIN).state !== "in-atlas"; }],
  ["stateOf: an empty list read as a mark", { "receipts.js": [['return m.length ? done("in-atlas", L[key]) : done("nothing-to-send");', 'return done("in-atlas", L[key]);']] }, async (dir) => { const m = await load(dir); return m.stateOf("k4", LIVE, MAIN).state !== "nothing-to-send"; }],
  ["the script's copy diverges (going-live read as in-atlas)", { "receipts.client.js": [['done("going-live", M[key])', 'done("in-atlas", M[key])']] }, async (dir) => equivalence(clientOf(dir)).length > 0],
  ["the script's copy trusts any href", { "receipts.client.js": [['if (t.indexOf(ORIGIN + "/") === 0', 'if (true']] }, async (dir) => equivalence(clientOf(dir)).length > 0],
  ["pulse: nothing-to-send rows counted in the tally", { "pulse.js": [['const makes = n.in + n.going + n.notSent;', 'const makes = n.in + n.going + n.notSent + n.nothing;']] }, async (dir) => { const m = await load(dir, "pulse.js"); const x = m.buildPulse({ searched: ROWS, receipts: rc, today: "2026-11-12" }); return x.days.find((q) => q.iso === "2026-11-12").atlasTally !== " · 1 of 4 in the Atlas" || x.days.find((q) => q.iso === "2026-11-11").atlasTally !== ""; }],
  ["pulse: logOnly taken from any truthy value", { "pulse.js": [['logOnly: r.logOnly === true', 'logOnly: !!r.logOnly']] }, async (dir) => { const m = await load(dir, "pulse.js"); return m.buildPulse({ searched: [{ when: "2026-11-12", outcome: "found", logOnly: "no" }], today: "2026-11-12" }).entries[0].updated.logOnly === true; }],
];
for (const [name, edits, caught] of FAULTS) {
  let c = false, why = "";
  try { const dir = copy("f" + n, edits); c = await caught(dir); } catch (e) { why = String(e.message || e); }
  ok("fault: " + name + " is caught", c, why);
}
fs.rmSync(tmp, { recursive: true, force: true });
console.log(bad ? `\n${bad} of ${n} FAILED` : `\nreceipts_logic: ${n} checks ok`);
process.exit(bad ? 1 : 0);
