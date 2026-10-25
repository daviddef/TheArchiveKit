// node kit/tools/story_logic.mjs : the small rules under the family story (lib/story.js, lib/mapgeom.js), held to the shared
// cases (kit/data/story-cases.json, which checkfamilystory.py answers too) and to arithmetic worked by hand.
//
//   shared    what a date is, what an initial is, what an extent is, what is inside one: the same answers as the gate
//   maps      the three projections, on boxes whose answers can be worked out; a clipped ring stays in its box; a leg ends
//             short of its far dot
//   prose     a link is made from [words](target); person: goes through the archive's own address; rec: is left to its
//             renderer; nothing the data holds can inject markup
//   living    the layout prints no year for a node, a card or an at-line flagged living, whatever the data holds
//   tree      the thread, the stem, the height; each grandchild hangs under its own parent (`of`), a child with none has no stem
//   proof     the date rule is shown to fail when it is broken
import fs from "fs"; import path from "path"; import { fileURLToPath } from "url";
import * as S from "../lib/story.js";
import * as G from "../lib/mapgeom.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const CASES = JSON.parse(fs.readFileSync(path.join(kit, "data", "story-cases.json"), "utf8"));
const PRESETS = JSON.parse(fs.readFileSync(path.join(kit, "data", "story-extents.json"), "utf8")).extents;
let bad = 0, n = 0;
const eq = (label, got, want) => { n++; const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) { bad++; console.log("  FAIL  " + label + "\n         got  " + JSON.stringify(got) + "\n         want " + JSON.stringify(want)); } else console.log("  ok    " + label); };
const near = (label, got, want, tol = 0.06) => { n++; const ok = Math.abs(got - want) <= tol; if (!ok) { bad++; console.log("  FAIL  " + label + "  got " + got + " want " + want); } else console.log("  ok    " + label); };

console.log("the shared cases");
eq("dates", CASES.dates.filter((c) => S.hasDate(c.text) !== c.date).map((c) => c.text), []);
eq("initials", CASES.initials.filter((c) => S.isInitial(c.name) !== c.initial).map((c) => c.name), []);
eq("whose child a grandchild is (the gate's T4, T5)", CASES.grandchildren.filter((c) => {
  const rows = (c.children ? [{ kind: "children", nodes: c.children.map((k) => ({ id: k, name: k })) }] : []).concat([{ kind: "grandchildren", nodes: c.grand.map((o, i) => (o === null ? { id: "g" + i, name: "g" } : { id: "g" + i, name: "g", of: o })) }]);
  return JSON.stringify(S.grandchildFaults({ rows })) !== JSON.stringify(c.codes);
}).map((c) => c.label), []);
eq("extents", CASES.extents.filter((c) => (G.resolveExtent(c.extent, PRESETS) !== null) !== c.ok).map((c) => c.extent), []);
eq("inside", CASES.inside.filter((c) => G.inExtent(G.resolveExtent(c.extent, PRESETS), c.lat, c.lon) !== c.in).map((c) => c), []);

console.log("maps");
const box = { west: 0, east: 10, south: 40, north: 50, projection: "equirectangular" };
const eqr = G.makeProjection(G.resolveExtent(box), 640);
near("equirectangular: the middle longitude is the middle of the picture", eqr.X(5), 320);
near("equirectangular: x is scaled by the cosine of the middle latitude, so 10 degrees of longitude are as wide as 7.07 of latitude", eqr.H, Math.round(10 * 640 / (10 * Math.cos(45 * Math.PI / 180))), 1);
near("equirectangular: the top edge is y 0", eqr.Y(50), 0);
near("equirectangular: the bottom edge is the height", eqr.Y(40), eqr.H, 1);
const pc = G.makeProjection(G.resolveExtent({ ...box, projection: "plate-carree" }), 640);
near("plate carree: ten degrees by ten make a square", pc.H, 640, 1);
const mc = G.makeProjection(G.resolveExtent({ ...box, projection: "mercator" }), 640);
near("mercator: x is linear in longitude", mc.X(2.5), 160);
eq("mercator: a degree of latitude is longer in the north than in the south", (mc.Y(41) - mc.Y(40)) < (mc.Y(50) - mc.Y(49)), false);
near("mercator: the top is y 0", mc.Y(50), 0);
const sq = [[-5, -5], [5, -5], [5, 5], [-5, 5]];
const cl = G.clipPoly(sq, [0, 0, 10, 10]);
eq("a ring clipped to a box stays in the box", cl.every(([x, y]) => x >= 0 && x <= 10 && y >= 0 && y <= 10), true);
eq("...and keeps the corner that was inside", cl.some(([x, y]) => x === 5 && y === 5), true);
eq("a ring wholly outside is nothing", G.clipPoly([[20, 20], [30, 20], [30, 30]], [0, 0, 10, 10]).length, 0);
eq("a border keeps only its runs inside", G.clipLine([[1, 1], [2, 2], [20, 20], [3, 3], [4, 4]], [0, 0, 10, 10]).map((r) => r.length), [2, 2]);
const curve = G.legCurve({ x: 0, y: 0 }, { x: 100, y: 0 }, 0);
eq("a straight leg runs along the chord", curve.d.startsWith("M0 0Q50 0 "), true);
const endX = Number(curve.d.split(" ").slice(-2)[0]);
near("a leg stops 6 units short of the far dot", 100 - endX, 6, 0.11);
eq("a path of fewer than two points is nothing", G.pathD([[1, 1]], true), "");

console.log("prose");
const id = (s) => s;
const o = { u: (p) => "/b" + p, personHref: (s) => `/b/people/${s}/` };
eq("an internal link goes through the archive's address", S.proseHtml("See [the line](/gologorica-line/#casa31).", id, o), 'See <a href="/b/gologorica-line/#casa31">the line</a>.');
eq("person: goes through the archive's person address", S.proseHtml("[him](person:ivan-1925)", id, o), '<a href="/b/people/ivan-1925/">him</a>');
eq("an #anchor is left alone", S.proseHtml("[below](#unknown)", id, o), '<a href="#unknown">below</a>');
eq("an outside address opens with noopener", S.proseHtml("[x](https://example.org/a)", id, o), '<a href="https://example.org/a" rel="noopener">x</a>');
eq("a rec: link is left for the archive's renderer", S.proseHtml("[x](rec:abc)", id, o), "[x](rec:abc)");
eq("plainText strips links and markup", S.plainText("A [link](/a/) and *an emphasis*, «quoted»."), "A link and an emphasis, quoted.");

console.log("the ribbon and the living");
const living = { name: "R", living: true, years: "1980–", atPlace: "Port Alder", atYear: "2005" };
eq("a living card prints no years", S.yearsLine(living), "");
eq("a living card's at-line prints no year", S.atLine(living), "at Port Alder");
eq("a dead card's at-line prints its year", S.atLine({ ...living, living: false }), "at Port Alder, 2005");
eq("no place, no at-line", S.atLine({ atPlace: "", atYear: "1850" }), "");
eq("a living node prints no years", S.nodeYears({ living: true, years: "1980" }), "");
eq("a living node's tip says so and has no date", S.nodeTip({ living: true, name: "Mira", years: "1981" }), "Mira: a living person, with no dates");
eq("a nameless living node is a living person", S.nodeTip({ living: true, name: "living" }), "A living person, drawn without name or dates");
eq("a dead node's tip has the grade in words", S.nodeTip({ name: "Tomas", years: "1790", grade: "inf" }), "Tomas, 1790 (inferred)");

console.log("the book");
const book = { ribbon: { cards: [{ chapter: "a" }, { chapter: "b" }, { chapter: "b" }, { chapter: "c" }] }, chapters: [{ id: "a" }, { id: "b" }, { id: "c", generation: [5, 6, 7] }] };
eq("generations: one, two and a stated list", S.generationsOf(book), { a: "1", b: "2 and 3", c: "5, 6 and 7" });
eq("world leads: only the first of a run", S.worldLeads([{ register: "people" }, { register: "world" }, { register: "world" }, { register: "people" }, { register: "world" }]), [false, true, false, false, true]);
eq("a people paragraph has one mark, its grade", S.marksOf({ grade: "inf", evidence: [{ href: "/x/", why: "w" }] }), [{ kind: "inf", href: "/x/", why: "w" }]);
eq("a world paragraph has a mark per source", S.marksOf({ register: "world", worldSource: "archive", evidence: [{ href: "/a/", kind: "archive" }, { href: "/h/", kind: "history" }] }).map((m) => m.kind), ["archive", "history"]);
eq("a world mark without a kind takes the paragraph's", S.marksOf({ register: "world", worldSource: "history", evidence: [{ href: "/h/" }] })[0].kind, "history");
eq("paragraph ids are made from the chapter and the place", S.paragraphsOf({ id: "ship", paragraphs: [{ text: "a" }, { id: "own", text: "b" }] }).map((p) => p.id), ["ship-1", "own"]);

console.log("the tree");
const tree = { thread: "pieter", rows: [
  { kind: "couple", nodes: [{ id: "t", name: "Tomas", grade: "doc" }, { id: "i", name: "Ilse", grade: "doc" }] },
  { kind: "children", nodes: [{ id: "anna", name: "Anna", grade: "doc" }, { id: "pieter", name: "Pieter", grade: "inf" }] }] };
const L1 = S.layoutTree(tree, false), L2 = S.layoutTree(tree, true);
eq("the child who carries the line is found", L1.lineKid && L1.lineKid.n.id, "pieter");
eq("a following chapter makes room for the way on", L2.H - L1.H, 22);
eq("the stem runs from the couple to the last child", [L1.stemTop, L1.lastY > L1.stemTop], [14, true]);
const upTree = { thread: "t", rows: [{ kind: "above", nodes: [{ id: "t", name: "T", grade: "doc" }] }, { kind: "gap", text: "no paper joins them" }, { kind: "above", nodes: [{ id: "u", name: "U", grade: "doc" }] }] };
const up = S.layoutTree(upTree);
eq("a thread on the person above is drawn down the stem", [up.aboveThread, up.gaps.length], [26, 1]);
eq("a tree with no thread has none", S.layoutTree({ rows: tree.rows }).lineKid, null);
const livingTree = { thread: "k", rows: [{ kind: "couple", nodes: [{ id: "r", name: "Rowan", living: true, years: "1980" }, { id: "m", name: "Mira", living: true }] }, { kind: "children", nodes: [{ id: "k", name: "K.", living: true, minor: true, years: "2015" }] }] };
eq("the description of a living tree has no date in it", S.hasDate(S.treeAlt(livingTree, "Us")), false);
eq("...and says who carries the line", S.treeAlt(livingTree, "Us").includes("K., living"), true);
eq("treeNodes lists every node but not a gap", S.treeNodes(upTree).length, 2);

console.log("the tree: each grandchild hangs under its own parent (`of`)");
const sisters = { thread: "u-cristina", rows: [
  { kind: "couple", nodes: [{ id: "u-g", name: "Giuseppina", living: true }, { id: "u-i", name: "Ian", living: true }] },
  { kind: "children", nodes: [{ id: "u-cristina", name: "Cristina", living: true }, { id: "u-stefanie", name: "Stefanie", living: true }] },
  { kind: "grandchildren", nodes: [
    { id: "u-a", name: "A.", living: true, minor: true, of: "u-cristina" }, { id: "u-m", name: "M.", living: true, minor: true, of: "u-cristina" },
    { id: "u-r", name: "R.", living: true, minor: true, of: "u-stefanie" }, { id: "u-m2", name: "M.", living: true, minor: true, of: "u-stefanie" }] }] };
const LS = S.layoutTree(sisters, true);
const kidsOf = LS.rows.find((r) => r.kind === "children").kids;
const [cri, ste] = kidsOf;
eq("the sisters' children hang under their own mother", [cri.sub.map((g) => g.n.id), ste.sub.map((g) => g.n.id)], [["u-a", "u-m"], ["u-r", "u-m2"]]);
eq("...and no row of grandchildren is drawn by itself", LS.rows.filter((r) => r.kind === "grand").length, 0);
eq("Cristina's children are drawn between Cristina and Stefanie, Stefanie's after her", [cri.sub.every((g) => g.y > cri.y && g.y < ste.y), ste.sub.every((g) => g.y > ste.y)], [true, true]);
eq("the thread still runs to the sister who carries the line", [LS.lineKid.n.id, LS.lineKid.y === cri.y], ["u-cristina", true]);
eq("the stem to the last child ends at Stefanie, not at the last grandchild", LS.lastY, ste.y);
eq("the picture is tall enough for the last grandchild", LS.H > ste.sub[ste.sub.length - 1].y, true);
const alt = S.treeAlt(sisters, "Us");
eq("the description says whose children they are", [alt.includes("Cristina's children: A., M."), alt.includes("Stefanie's children: R., M.")], [true, true]);
eq("...and has no date in it, and no doubled stop after an initial", [S.hasDate(alt), alt.includes("..")], [false, false]);
const mixed = { rows: [{ kind: "children", nodes: [{ id: "a", name: "Anna", years: "1820\u20131824", grade: "doc" }, { id: "b", name: "Bea", years: "1822", grade: "doc" }, { id: "c", name: "Cy", years: "1825", grade: "inf" }] },
  { kind: "grandchildren", nodes: [{ id: "x", name: "Xan", years: "1850", grade: "doc", of: "c" }] }] };
const LM = S.layoutTree(mixed).rows[0].kids;
eq("children with none have no stem (and the one with a child is the third)", LM.map((k) => k.sub.length), [0, 0, 1]);
eq("...and a child with none leaves no gap behind it", [LM[1].y - LM[0].y, LM[2].y - LM[1].y], [27, 27]);
eq("a dead grandchild's description has the years and the grade", S.treeAlt(mixed, "T").includes("Cy's children: Xan 1850, documented."), true);
const one = { rows: [{ kind: "children", nodes: [{ id: "a", name: "Ivone", grade: "doc" }] }, { kind: "grandchildren", nodes: [{ id: "h", name: "Henrique", grade: "inf" }, { id: "d", name: "D.", living: true }] }] };
eq("with one child, `of` may be left out: they hang under that child", S.layoutTree(one).rows[0].kids[0].sub.map((g) => g.n.id), ["h", "d"]);
const amb = { thread: "b", rows: [{ kind: "children", nodes: [{ id: "a", name: "A", grade: "doc" }, { id: "b", name: "B", grade: "doc" }, { id: "c", name: "C", grade: "doc" }] }, { kind: "grandchildren", nodes: [{ id: "h", name: "H", grade: "doc" }] }] };
const LA = S.layoutTree(amb).rows[0].kids;
eq("with several children and no `of` (the gate fails it) the drawing never picks the last child by luck: it uses the thread child", LA.map((k) => k.sub.length), [0, 1, 0]);
eq("...and the description says the parent is not named", S.treeAlt(amb, "T").includes("a parent the data does not name"), true);
const dangling = { rows: [{ kind: "children", nodes: [{ id: "a", name: "A", grade: "doc" }, { id: "b", name: "B", grade: "doc" }] }, { kind: "grandchildren", nodes: [{ id: "h", name: "H", grade: "doc", of: "nobody" }] }] };
eq("an `of` that names no one is not drawn under a guess of its own: it is loose, like the missing one", S.grandchildGroups(dangling)[0].loose.map((g) => g.id), ["h"]);
eq("a grandchildren row with no children above is a column of its own", S.layoutTree({ rows: [{ kind: "couple", nodes: [{ id: "p", name: "P", grade: "doc" }] }, { kind: "grandchildren", nodes: [{ id: "h", name: "H", grade: "doc" }] }] }).rows.map((r) => r.kind), ["couple", "grand"]);
eq("a living nameless parent's group is announced without a name", S.possessive({ living: true, name: "living" }), "the living person's");
eq("a name ending in s takes only the stop", S.possessive({ name: "Lucas" }), "Lucas'");

console.log("proof: the shared cases are shown to fail a broken rule");
const weakDate = (t) => /\b1[0-9]{3}\b/.test(t);              // four digits, no months, no 20xx
const anyInitial = (t) => /^[A-Z.]{1,3}$/.test(t);              // lets lower case and a bare stop through, no accents
const strictExtent = (e) => typeof e === "string" && !!PRESETS[e];  // forgets boxes and {preset}
eq("a date rule that forgot months and the 2000s is caught by the cases", CASES.dates.some((c) => weakDate(c.text) !== c.date), true);
eq("an initial rule that forgot accents is caught by the cases", CASES.initials.some((c) => anyInitial(c.name) !== c.initial), true);
const oldWay = (t) => { const k = t.rows.find((r) => r.kind === "children").nodes; return t.rows.find((r) => r.kind === "grandchildren").nodes.map(() => k[k.length - 1].id); };   // every grandchild under the last child
eq("the old rule (all under the last child) puts A. under Stefanie, which the `of` layout refuses", oldWay(sisters).join() !== cri.sub.concat(ste.sub).map((g, i) => (i < 2 ? "u-cristina" : "u-stefanie")).join(), true);
eq("a gate that only looked for a missing `of` is caught by the cases (it lets a dangling one through)", CASES.grandchildren.some((c) => c.codes.includes("T5")), true);
eq("a gate that forgot a one-child row may omit `of` is caught by the cases", CASES.grandchildren.some((c) => c.children && c.children.length === 1 && c.grand.includes(null) && c.codes.length === 0), true);
eq("an extent rule that forgot boxes is caught by the cases", CASES.extents.some((c) => strictExtent(c.extent) !== c.ok), true);

console.log(bad ? `\nstory_logic: ${bad} of ${n} FAILED` : `\nstory_logic: ${n}/${n} ok`);
process.exit(bad ? 1 : 0);
