// «Where we have looked» (lib/personlooked.js), tested without a build. The thing most worth proving is the honesty rule:
// a search that was NOT made never reads like one that found nothing, and a nothing is only drawn where every spelling was covered.
//   node kit/tools/personlooked_logic.mjs
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const L = await import(pathToFileURL(path.join(here, "..", "lib", "personlooked.js")).href);

let n = 0, bad = 0;
const eq = (label, got, want) => {
  n++;
  if (JSON.stringify(got) !== JSON.stringify(want)) { bad++; console.log(`  FAIL  ${label}\n        got  ${JSON.stringify(got)}\n        want ${JSON.stringify(want)}`); }
};
const throws = (label, fn, rx) => {
  n++;
  try { fn(); bad++; console.log(`  FAIL  ${label} (did not throw)`); }
  catch (e) { if (!rx.test(e.message)) { bad++; console.log(`  FAIL  ${label}\n        threw ${e.message}`); } }
};

const V = (id, f, to, t = "Births " + f + "-" + to) => ({ id, t, u: "https://example.test/" + id, f, to });
const placeA = { key: "aville", name: "Aville", volumes: [V("v1", 1800, 1830), V("v2", 1831, 1860), V("v3", 1861, 1890), V("v4", 1891, 1920)], held: { books: "Births 1800-1920", checked: "checked" } };
const placeB = { key: "bton", name: "Bton", volumes: [] };
const row = (id, outcome, extra = {}) => ({ id, src: "Source " + id, outcome, surnames: ["fox"], places: ["aville"], volumes: [], when: "1 January 2026", ...extra });

/* the five words become five classes, and the unknown word is refused */
const R = [
  row("a", "yield", { volumes: ["v1"] }),
  row("b", "partial", { volumes: ["v2"] }),
  row("c", "nothing", { volumes: ["v3"], nil: { status: "covered", missed: [] } }),
  row("d", "pending", { volumes: ["v4"] }),
];
const m = L.lookedModel({ rows: R, places: [placeA], names: ["Fox"], span: null });
eq("classes: found, partial, nil, notyet", m.groups[0].rows.map((r) => r.cls), ["found", "partial", "nil", "notyet"]);
eq("a covered nil is the only row drawn as «nothing found»", m.groups[0].rows.filter((r) => r.cls === "nil").map((r) => r.id), ["c"]);
eq("progress counts volumes looked at (found, partial and nil), not the pending one", [m.groups[0].looked.length, m.groups[0].total, m.groups[0].inPart], [3, 4, 1]);
eq("the pending volume is listed as not yet looked at, with its state kept", m.groups[0].unopened.map((v) => [v.id, v.state]), [["v4", "notyet"]]);
eq("the progress line says so in words", m.progress, ["Aville: the Record Atlas lists 4 volumes; 3 have been looked at for Fox (1 only in part)."]);

/* THE RULE: a nil is not an absence unless every spelling was covered */
for (const [label, nil, want] of [
  ["a nil with no verdict", undefined, "nilx"], ["a nil with an unknown verdict", { status: "unknown" }, "nilx"],
  ["a nil that missed a spelling", { status: "missed", missed: ["Fax"] }, "nilx"], ["a covered nil", { status: "covered" }, "nil"],
]) eq(`${label} is drawn as ${want}`, L.drawnClass(row("x", "nothing", { nil })), want);
const mm = L.lookedModel({ rows: [row("x", "nothing", { nil: { status: "missed", missed: ["Fax", "Fox"] } })], places: [placeA], names: ["Fox"] });
eq("a nil that missed spellings NAMES them and says it is not an absence", mm.groups[0].rows[0].nilnote, "Not shown as an absence: Fax and Fox were not tried in this search, and the Record Atlas lists them as a spelling of the name.");
eq("a nil with no verdict says the spellings are not recorded", L.nilNote(row("x", "nothing")).startsWith("Not shown as an absence: the spellings typed are not recorded"), true);
eq("a covered nil carries no note", L.nilNote(row("x", "nothing", { nil: { status: "covered" } })), "");
eq("a row that is not a nil never gets a nil note, whatever verdict it carries", L.lookedModel({ rows: [row("x", "yield", { nil: { status: "missed", missed: ["Fax"] } })], places: [placeA], names: ["Fox"] }).groups[0].rows[0].nilnote, "");
eq("blocked and pending are not searches that were made", L.lookedModel({ rows: [row("p", "blocked", { volumes: ["v1"] }), row("q", "pending", { volumes: ["v2"] })], places: [placeA], names: ["Fox"] }).groups[0].looked.length, 0);
eq("a nil whose spelling was missed still counts as the volume having been opened", L.lookedModel({ rows: [row("x", "nothing", { volumes: ["v1"], nil: { status: "missed", missed: ["Fax"] } })], places: [placeA], names: ["Fox"] }).groups[0].looked.length, 1);

/* the years only ORDER the unopened volumes: nothing is dropped for being outside a life (a parent's marriage is in an earlier volume) */
const ms = L.lookedModel({ rows: [], places: [placeA], names: ["Fox"], span: [1840, 1870] });
eq("the volumes in the person's years come first, then the nearest", ms.groups[0].unopened.map((v) => v.id), ["v2", "v3", "v1", "v4"]);
eq("none is dropped", ms.groups[0].unopened.length, 4);
eq("with no years, every unopened volume is listed in the Atlas's order", L.lookedModel({ rows: [], places: [placeA], names: ["Fox"] }).groups[0].unopened.map((v) => v.id), ["v1", "v2", "v3", "v4"]);
eq("a volume with no years is listed with the rest", L.lookedModel({ rows: [], places: [{ ...placeA, volumes: [{ id: "u", t: "A census", f: null, to: null }] }], names: ["Fox"], span: [1840, 1870] }).groups[0].unopened.length, 1);
const mv = L.lookedModel({ rows: [], places: [{ ...placeA, volumes: Array.from({ length: 9 }, (_, i) => V("x" + i, 1800 + i, 1800 + i)) }], names: ["Fox"] });
eq("the first six are listed, the rest folded away", [mv.groups[0].shownVols.length, mv.groups[0].moreVols.length], [6, 3]);

/* a place with no Atlas volume says so, and has no count */
const mb = L.lookedModel({ rows: [row("z", "yield", { places: ["bton"] })], places: [placeB], names: ["Fox"] });
eq("a place the Atlas lists nothing for has no progress line", mb.progress, []);
eq("and is named", mb.noAtlas, ["Bton"]);

/* each row once, under the place of the volume it read */
const two = L.lookedModel({ rows: [row("w", "yield", { places: ["aville", "bton"], volumes: ["v2"] })], places: [placeB, placeA], names: ["Fox"] });
eq("a row that names two places is listed once, under the place of its volume", [two.groups[0].rows.length, two.groups[1].rows.length], [0, 1]);
eq("the counts agree", two.counts.rows, 1);

/* the tag sentence */
eq("rows matched by tag say so", L.lookedModel({ rows: [row("a", "yield")], places: [placeA], names: ["Fox"] }).byTag, true);
eq("rows that are the person's own do not", L.lookedModel({ rows: [row("a", "yield", { own: true })], places: [placeA], names: ["Fox"] }).byTag, false);

/* the cap hides only what was found or read in part: a nothing is never folded away */
const many = Array.from({ length: 12 }, (_, i) => row("m" + i, i % 3 === 0 ? "nothing" : "yield", { nil: { status: "covered" } }));
const mc = L.lookedModel({ rows: many, places: [placeA], names: ["Fox"], cap: 5 });
eq("a cap shows that many found rows, every nothing, and counts the rest", [mc.groups[0].shown.length, mc.groups[0].hidden.length, mc.groups[0].hiddenBy], [9, 3, { found: 3 }]);
eq("every nil is still shown", mc.groups[0].shown.filter((r) => r.cls === "nil").length, 4);
eq("the cap never changes the counts", mc.counts.rows, 12);
eq("below the cap nothing is hidden", L.lookedModel({ rows: many, places: [placeA], names: ["Fox"], cap: 8 }).groups[0].hidden.length, 0);

/* something wanted at the place is not a search for the name */
const w = L.lookedModel({ rows: [row("w1", "pending", { placeOnly: true, surnames: [] }), row("a", "yield")], places: [placeA], names: ["Fox"] });
eq("a place-only row is listed as wanted, not as a search", [w.groups[0].wanted.map((r) => r.id), w.groups[0].rows.map((r) => r.id), w.counts.rows, w.counts.wanted], [["w1"], ["a"], 1, 1]);
eq("a place-only row alone does not make the match «by tag»", L.lookedModel({ rows: [row("w1", "pending", { placeOnly: true })], places: [placeA], names: ["Fox"] }).byTag, false);
throws("a place-only row that claims a search was made", () => L.lookedModel({ rows: [row("w2", "yield", { placeOnly: true })], places: [placeA], names: ["Fox"] }), /placeOnly/);

/* refusals */
throws("an outcome word the archive did not declare", () => L.lookedModel({ rows: [row("a", "perhaps")], places: [placeA], names: ["Fox"] }), /no class/);
throws("a row that names none of the person's places", () => L.lookedModel({ rows: [row("a", "yield", { places: ["elsewhere"] })], places: [placeA], names: ["Fox"] }), /names none of this person's places/);
eq("another archive's outcome vocabulary is taken as given", L.drawnClass({ outcome: "empty" }, { empty: { label: "Empty", cls: "nil" } }), "nilx");
eq("names join in words", L.listJoin(["A", "B", "C"]), "A, B and C");

console.log(`  personlooked_logic: ${n - bad} of ${n} cases hold`);
process.exit(bad ? 1 : 0);
