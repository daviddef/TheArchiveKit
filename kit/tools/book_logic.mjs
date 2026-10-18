// node kit/tools/book_logic.mjs : the book's order and placement, held to the shared cases (kit/data/book-cases.json)
import fs from "fs"; import path from "path"; import { fileURLToPath } from "url";
import * as B from "../lib/book.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const FIX = JSON.parse(fs.readFileSync(path.join(here, "..", "data", "book-cases.json"), "utf8"));
let bad = 0, n = 0;
const eq = (label, got, want) => { n++; const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) { bad++; console.log("  FAIL  " + label + "\n         got  " + JSON.stringify(got) + "\n         want " + JSON.stringify(want)); } else console.log("  ok    " + label); };
const summarise = (r, want) => {
  if (want.nowhere) return { nowhere: r === null };
  if (want.outside) return { outside: !!(r && r.outside) };
  if (!r || r.outside) return { got: r };
  const o = { kind: r.entry.kind, n: r.n };
  for (const k of Object.keys(want)) {
    if (k === "kind" || k === "n") continue;
    if (k === "prev") o.prev = r.prev ? r.prev.path : null;
    else if (k === "next") o.next = r.next ? r.next.path : null;
    else if (k === "part") o.part = r.part ? r.part.id : null;
    else if (k === "inherited") o.inherited = r.inherited;
    else if (k === "via") o.via = r.via;
  }
  return o;
};
const runAll = (lib) => FIX.cases.map((c) => [c, summarise(lib.locate(FIX.book, c.path), c.want)]);
eq("the fixture book has the expected number of entries", B.flatten(FIX.book).length, FIX.total);
for (const [c, got] of runAll(B)) eq(c.id, got, c.want);
// planted faults: a copy of book.js with one rule broken must fail the shared cases
const src = fs.readFileSync(path.join(here, "..", "lib", "book.js"), "utf8");
const faults = [
  ["Previous/Next ignore the opener", "out.push({ path: openerPath(part), title: part.title, blurb: part.intro || \"\", kind: \"opener\", part: i, group: \"\" });", "", "opener-follows-front"],
  ["a path is not normalised", "if (!s.endsWith(\"/\") && !/\\.[a-z0-9]+$/i.test(s)) s += \"/\";", "", "data-without-slash-is-normalised"],
  ["inheritance matches the index itself", "if (p.startsWith(pre) && p !== pre) {", "if (p.startsWith(pre)) {", "an-index-itself-is-not-inherited"],
  ["an outside page is not outside", "if ((book.outside || []).map(norm).includes(p)) return { outside: true };", "", "outside-page"],
  ["outside is read after inherit", "  if ((book.outside || []).map(norm).includes(p)) return { outside: true };\n", "", "outside-beats-inherit",
    ["  return null;\n}\n\n/* Every page", "  if ((book.outside || []).map(norm).includes(p)) return { outside: true };\n  return null;\n}\n\n/* Every page"]],
  ["an inherited page gets a next link", "prev: null, next: null, part: partOf(e), inherited: true", "prev: null, next: entries[j + 1] || null, part: partOf(e), inherited: true", "who-page-inherits-another-chapter"],
];
const os = await import("os"), pu = await import("url");
for (const [label, from, to, must, extra] of faults) {
  if (!src.includes(from)) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; }
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "book-fault-")); const f = path.join(d, "book.mjs");
  let broken = src.replace(from, to); if (extra) { if (!broken.includes(extra[0])) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; } broken = broken.replace(extra[0], extra[1]); }
  fs.writeFileSync(f, broken);
  const M = await import(pu.pathToFileURL(f).href);
  const failed = runAll(M).filter(([c, got]) => JSON.stringify(got) !== JSON.stringify(c.want)).map(([c]) => c.id);
  n++; if (failed.includes(must)) console.log("  ok    planted fault '" + label + "' is caught (" + must + ")"); else { bad++; console.log("  FAIL  planted fault '" + label + "' was NOT caught"); }
  fs.rmSync(d, { recursive: true, force: true });
}
console.log(bad ? "\n" + bad + " of " + n + " FAILED" : "\n  ok    " + n + " checks: the order of the book and where each page sits");
process.exit(bad ? 1 : 0);
