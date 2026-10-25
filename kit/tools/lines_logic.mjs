// node kit/tools/lines_logic.mjs : the words and the arithmetic of the lines drawing (lib/lines.js, and the layout
// numbers in components/BranchRivers.astro's frontmatter), held to the shared cases (kit/data/lines-cases.json) and to
// what the older component drew, so an archive pinned to either gets the same picture.
//
//   status   the same lane gives the same words here and in checklines.py
//   pens     the two old lists become two pens; `pens` wins; an empty pen is not drawn; counts are derived
//   layout   with the old data the block is exactly the numbers it always was (second heading +80, block 124, 146 tall);
//            a note adds 15 a line; more rows add 26 each; unplacedAfter moves the block and the stack follows
//   links    a slug is built under personBase, a path is a path
//   proof    the layout check is shown to fail when the arithmetic is broken
import fs from "fs"; import path from "path"; import { fileURLToPath } from "url";
import * as L from "../lib/lines.js";
import { plain } from "../lib/md.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const CASES = JSON.parse(fs.readFileSync(path.join(kit, "data", "lines-cases.json"), "utf8"));
let bad = 0, n = 0;
const eq = (label, got, want) => { n++; const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) { bad++; console.log("  FAIL  " + label + "\n         got  " + JSON.stringify(got) + "\n         want " + JSON.stringify(want)); } else console.log("  ok    " + label); };

console.log("status");
for (const c of CASES.status) eq(c.id, L.statusLine(c.lane).text, c.text);
eq("a lane with a status has a tier", L.statusLine({ status: "inferred" }).tier, "inferred");
eq("a lane with only conf is legacy and has no tier", [L.statusLine({ conf: "x" }).tier, L.statusLine({ conf: "x" }).legacy], [null, true]);

console.log("pens");
const legacy = { lanes: [], unplaced: [["Rijeka", "/r/", "a"], ["Medulin", "/m/", "b"]], loose: [["Brazil", "/d/", "c"]], looseNote: "- the commonest" };
const P = L.pensOf(legacy);
eq("the two old lists become two pens, in the old order", P.map((p) => [p.kind, p.items.length]), [["not-yet-placed", 2], ["different-stock", 1]]);
eq("the old looseNote is the different-stock pen's note", P[1].note, "- the commonest");
eq("the default headings are the old ones", [P[0].head, P[1].head], [L.HEAD_DEFAULT["not-yet-placed"], L.HEAD_DEFAULT["different-stock"]]);
eq("an empty old list draws no pen", L.pensOf({ unplaced: [], loose: [], unplacedHead: "A heading" }).length, 0);
eq("`pens` wins over the old lists", L.pensOf({ pens: [{ kind: "different-stock", items: [["x", "/", ""]] }], unplaced: [["a", "/", ""]] }).map((p) => p.kind), ["different-stock"]);
eq("a pen with only members is drawn", L.pensOf({ pens: [{ kind: "not-yet-placed", members: ["a-b"] }] }).length, 1);
eq("a pen with neither is not", L.pensOf({ pens: [{ kind: "not-yet-placed", head: "h", items: [], members: [] }] }).length, 0);
eq("a member may be a slug or an object", L.pensOf({ pens: [{ members: ["a", { person: "b", reason: "r" }] }] })[0].members.map((m) => [m.person, m.reason]), [["a", ""], ["b", "r"]]);
const withP = L.pensOf({ pens: [{ kind: "not-yet-placed", items: [["a", "/", ""], ["b", "/", ""]], members: ["x", "y", "z"], count: 99 }] })[0];
eq("members decide the count, not a stale `count`", withP.people, 3);
eq("the heading count is derived", L.penCount(withP), "2 households · 3 people");
eq("one household, one person", L.penCount(L.pensOf({ pens: [{ items: [["a", "/", ""]], members: ["x"] }] })[0]), "1 household · 1 person");
eq("a different-stock pen is `kept apart`, not households", L.penCount(P[1]), "1 kept apart");
eq("a count with no members is kept", L.pensOf({ pens: [{ items: [["a", "/", ""]], count: 31 }] })[0].people, 31);

console.log("nodes, people, links");
eq("an old node array and an object come out alike", [L.node(["Pula", "1659", "w"]).place, L.node({ place: "Pula", year: "1659", why: "w" }).year], ["Pula", "1659"]);
eq("a slug is built under personBase", L.personPath("ada-alder"), "/people/ada-alder/");
eq("personBase may be another route", L.personPath("ada-alder", "/who"), "/who/ada-alder/");
eq("a path is a path", L.personPath("/people/ada-alder/#born"), "/people/ada-alder/#born");
eq("a slug with no page name is read as a name", L.slugName("lucia-defranceschi-1844"), "Lucia Defranceschi 1844");
eq("lane people: nodes' persons and members, once each", L.lanePeople({ nodes: [{ place: "a", person: "x" }, ["b", "1", "w"], { place: "c", person: "x" }], members: ["y", { person: "x" }] }).sort(), ["x", "y"]);
eq("evidence `register` is read; `lore` is soft", [L.evidenceOf("register").soft, L.evidenceOf("lore").soft], [false, true]);
eq("an unknown evidence word is kept, visibly unmarked", [L.evidenceOf("hearsay").key, L.evidenceOf("hearsay").known], ["unmarked", false]);
eq("no evidence is no mark", L.evidenceOf(null), null);

console.log("wrap and clip");
eq("a long note wraps at a word, no line over the limit", L.wrap("one two three four five six", 12), ["one two", "three four", "five six"]);
eq("a note's markup is stripped before it wraps", L.wrap("**bold** «quoted» word", 40), ["bold quoted word"]);
eq("a label is clipped at a word with an ellipsis", L.clip("Rijeka — Fiume, Vitipolis and the rest of it", 24), "Rijeka — Fiume,…".replace("Fiume,…", "Fiume…"));
eq("a short label is left alone", L.clip("Brazil", 34), "Brazil");

console.log("ledger");
const lg = L.ledger({ lanes: [{ status: "documented", nodes: [{ place: "a", person: "x" }] }, { status: "family-lore", nodes: [] }, { conf: "old", nodes: [] }],
  pens: [{ kind: "not-yet-placed", items: [["a", "/", ""], ["b", "/", ""]], members: ["p", "q"] }, { kind: "different-stock", items: [["c", "/", ""]] }], bridges: [{}] });
eq("every count is read from the data", [lg.lanes, lg.unstated, lg.households, lg.otherStock, lg.bridges, lg.peopleOnLanes, lg.peopleInPens, lg.tiers.documented], [3, 1, 2, 1, 1, 1, 2, 1]);

console.log("layout (the component's own frontmatter, run on fixture props)");
const SRC = fs.readFileSync(path.join(kit, "components", "BranchRivers.astro"), "utf8");
function layout(src, rivers) {
  const a = src.indexOf("---"), b = src.indexOf("\n---", a + 3);
  const body = src.slice(a + 3, b).replace(/^import [\s\S]*?from ["'][^"']+["'];?$/gm, "").replace(/Astro\.props/g, "__props");
  /* the component imports two of these under other names */
  const env = { ...L, normNode: L.node, normMember: L.member, plain };
  const fn = new Function("__props", "u", ...Object.keys(env), `${body}\n return { PL, END, BLOCK, VH, LOOSE_Y, CUT, BANDS };`);
  return fn({ rivers, personBase: "/people/", names: {} }, (x) => x, ...Object.values(env));
}
const lane = (k) => ({ key: k, label: k, colour: "#000", href: "/", read: "r", nodes: [["a", "1", "w"], ["b", "2", "w"]], ends: [] });
const two = { lanes: [lane("a"), lane("b")], unplaced: [["x", "/", ""]], loose: [["y", "/", ""]] };
const g = layout(SRC, two);
eq("old data: the second heading is at +80 and its row at +100", [g.PL[1].t + 20, g.PL[1].itemsY0], [80, 100]);
eq("old data: the block is 124 tall below the rule, 146 with its gap", [g.END, g.BLOCK], [124, 146]);
eq("old data, one pen only: 64 and 86", [layout(SRC, { ...two, loose: [] }).END, layout(SRC, { ...two, loose: [] }).BLOCK], [64, 86]);
eq("old data: the drawing is 34 + 2*152 + 146 tall", g.VH, 34 + 2 * 152 + 146);
const wide = layout(SRC, { ...two, unplaced: Array.from({ length: 7 }, (_, i) => ["h" + i, "/", ""]) });
eq("seven households make three rows: 52 more", wide.END - g.END, 52);
const noted = layout(SRC, { ...two, looseNote: "word ".repeat(60) });
eq("a note of 300 characters wraps to 2 lines: the block ends 26 + 15 below where it did", noted.END - g.END, 41);
const mid = layout(SRC, { ...two, unplacedAfter: "a" });
eq("unplacedAfter puts the rule under lane a and the stack follows", [mid.CUT, mid.LOOSE_Y, mid.BANDS[1].y0 - layout(SRC, { ...two }).BANDS[1].y0], [1, 34 + 152 + 22, mid.BLOCK + 36]);
eq("no pens, no block", [layout(SRC, { lanes: [lane("a")] }).BLOCK, layout(SRC, { lanes: [lane("a")] }).VH], [0, 34 + 152]);

console.log("proof: the layout check fails when the arithmetic is broken");
const broken = SRC.replace("cursor = last + 20;", "cursor = last + 21;");
let caught = false; try { caught = layout(broken, two).END === g.END ? false : true; } catch { caught = true; }
eq("a pen gap of 21 instead of 20 moves the block", caught, true);
const broken2 = SRC.replace("const END = HAS_PENS ? PL[PL.length - 1].last + 24 : 0;", "const END = HAS_PENS ? PL[PL.length - 1].last + 25 : 0;");
eq("an end gap of 25 instead of 24 moves the block", layout(broken2, two).END !== g.END, true);

console.log(bad ? `\n${bad} of ${n} FAILED` : `\n${n} cases, all ok`);
process.exit(bad ? 1 : 0);
