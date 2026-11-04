// The story layer of a people page (lib/personstory.js, lib/personevidence.js), tested without a build, and with planted faults.
// The thing most worth proving is the living rule: a living relative is a name and a relationship, a held-out relative is absent,
// and nothing about either reaches the output however the tree is shaped.
//   node kit/tools/personstory_logic.mjs
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const lib = path.join(here, "..", "lib");
const S = await import(pathToFileURL(path.join(lib, "personstory.js")).href);
const E = await import(pathToFileURL(path.join(lib, "personevidence.js")).href);
const P = await import(pathToFileURL(path.join(lib, "person.js")).href);

let n = 0, bad = 0;
const eq = (label, got, want) => {
  n++;
  if (JSON.stringify(got) !== JSON.stringify(want)) { bad++; console.log(`  FAIL  ${label}\n        got  ${JSON.stringify(got)}\n        want ${JSON.stringify(want)}`); }
};

const RULE = { now: 2026, sources: [] };
const person = (id, given, sur, by, dy, extra = {}) => ({ id, given, sur, by, dy, bp: "Testville", href: `/person/${id}/`, kids: [], spouse: [], line: 1, ...extra });
// three generations: Anna (b.1840 d.1910) + Beno -> Carl (b.1870 d.1940) + Dora -> Eva (b.1905 d.1980) -> Frank (b.1950 d.2026) -> Greta (b.1985, alive) -> Hal (undated, parent Greta)
const T = {
  anna: person("anna", "Anna", "Fox", 1840, 1910), beno: person("beno", "Beno", "Fox", 1838, 1900),
  carl: person("carl", "Carl", "Fox", 1870, 1940, { father: "beno", mother: "anna" }), dora: person("dora", "Dora", "Fox", 1872, 1950),
  eva: person("eva", "Eva", "Fox", 1905, 1980, { father: "carl", mother: "dora" }),
  frank: person("frank", "Frank", "Fox", 1950, 2026, { father: "eva" }),
  greta: person("greta", "Greta", "Fox", 1985, null, { father: "frank" }),
  hal: person("hal", "Hal", "Fox", null, null, { mother: "greta" }),
  ivo: person("ivo", "Ivo", "Fox", 1952, null, { father: "eva" }),          // a brother of Frank, alive (b.1952)
  jan: person("jan", "Jan", "Fox", 1953, 2001, { father: "eva" }),          // a brother who died
};
for (const p of Object.values(T)) { p.kids = Object.values(T).filter((x) => x.father === p.id || x.mother === p.id).map((x) => x.id); }

/* the rule: who is living, who is held out */
eq("a person of 76 with no death is living", S.livingOf(T, "ivo", RULE), true);
eq("a person who died is not living", S.livingOf(T, "frank", RULE), false);
eq("an undated child of a living parent is held out", S.heldOutOf(T, "hal", RULE), true);
eq("a dated living person is not held out", S.heldOutOf(T, "greta", RULE), false);

/* a card */
const frank = S.famNode(T, "frank", "Father", "", RULE);
eq("a dead person carries years, place and link", [frank.dates, frank.place, frank.href], ["1950 – 2026", "Testville", "/person/frank/"]);
const greta = S.famNode(T, "greta", "Child", "", RULE);
eq("a living relative is a name only: no dates, no place; the name still links to their page", [greta.name, greta.living, greta.dates, greta.place, greta.href], ["Greta Fox", true, "", "", "/person/greta/"]);
eq("a held-out relative is not drawn at all", S.famNode(T, "hal", "Child", "", RULE), null);
eq("an unknown parent is a gap, said as one", S.famNode(T, "nobody", "Mother", "Mother not yet found", RULE), { unknown: true, rel: "Mother", missing: "Mother not yet found" });

/* the family of one person */
const fam = S.familyOf(T, "frank", RULE);
eq("brothers and sisters are found from the parent link and a living one is a name only",
   fam.siblings.map((x) => [x.name, x.dates, x.place, x.href]), [["Ivo Fox", "", "", "/person/ivo/"], ["Jan Fox", "1953 – 2001", "Testville", "/person/jan/"]]);
eq("children: the living one is drawn by name, the held-out grandchild is nowhere", fam.children.map((x) => x.name), ["Greta Fox"]);
eq("nobody held out appears in the family at all", JSON.stringify(S.familyOf(T, "greta", RULE)).includes("Hal"), false);
eq("an archive tree with the held-out child still gives the living parent a page of name and relationships", S.familyOf(T, "greta", RULE).children, []);
eq("the grandparents are placed by what they were to the person, an unknown one drawn as a gap", S.familyOf(T, "eva", RULE).grand.map((g) => [g.rel, !!g.unknown]), [["Father's father", false], ["Father's mother", false], ["Mother's father", true], ["Mother's mother", true]]);

/* the ancestry thread */
const th = S.ancestryOf(T, "frank", { place: "Origin" }, RULE);
eq("a thread climbs the father's line to the earliest we can document", [th[0].side, th[0].parent.name, th[0].earliest && th[0].earliest.name], ["Father's line", "Eva Fox", "Beno Fox"]);
eq("the mother's line, with no mother known, says so", [th[1].side, th[1].parent.missing, th[1].earliest], ["Mother's line", "Mother not yet found", null]);
eq("a thread of living people never carries their dates", JSON.stringify(S.ancestryOf(T, "hal", null, RULE)).includes("1985"), false);

/* grades: a person takes a grade, never the direct line */
eq("an ark alone is not a grade: it can name an index entry, which is ungraded by ruling", E.evidenceOf({ ark: "1:1:AAAA-BBB" }), null);
eq("a family-tree row that carries an ark is Family, not Documented", E.evidenceOf({ src: "tree", ark: "1:1:AAAA-BBB" }, { treeSrc: ["tree"] }), { tier: "tree", label: "Family" });
eq("an archive's own source kind counts only if it said so", E.evidenceOf({ src: "register" }), null);
eq("... and does when it did", E.evidenceOf({ src: "register" }, { docSrc: ["register"] }), { tier: "doc", label: "Documented" });
eq("a lore note is Family", E.evidenceOf({ note: "He sailed. *lore*" }), { tier: "lore", label: "Family" });
eq("a note graded both lore and inferred is Inferred", E.evidenceOf({ note: "*lore* then *inf*" }), { tier: "inf", label: "Inferred" });
eq("the direct line is not a grade", E.evidenceOf({ line: 0, direct: true }), null);
eq("every label is one of the kit's five grades", ["doc", "lore", "inf"].every((t) => P.GRADES.includes({ doc: "documented", lore: "family", inf: "inferred" }[t])), true);

/* the journey and the sentence about it */
const j = S.journeyOf({ place: "Senj → Harare → Brisbane", places: ["Senj, Croatia", "Harare, Zimbabwe", "Brisbane, Australia"], b: 1951, d: 2026, moves: [{ place: "Harare, Zimbabwe", y: 1970 }] });
eq("a journey has a country for each stop and a year for each it can", j.map((s) => [s.name, s.iso, s.kind, s.year]), [["Senj", "HR", "Born", 1951], ["Harare", "ZW", "Moved", 1970], ["Brisbane", "AU", "Died", 2026]]);
eq("a stop with no country anywhere has none, and none is guessed", S.journeyOf({ place: "Senj", b: 1951 })[0].country, "");
eq("the sentence is neutral about the person", S.lifeSentence(j, { b: 1951, d: 2026 }), "Born at Senj in 1951 and died at Brisbane in 2026, by way of Harare.");
eq("a death with no recorded arrival is a gap, and a stop with its year is not", S.gapsOf(j, [], "/person/x/").split("\n\n").filter((x) => x.startsWith("**")).map((x) => x.split("**")[1]), ["Brisbane, arrival."]);
eq("a stop with no year is a gap", S.gapsOf([{ kind: "Born", name: "A" }, { kind: "Moved", name: "B", year: null }], [], "/person/x/").startsWith("**B, no year.**"), true);
eq("the pointer to where to look uses the shared anchor", S.gapsOf([{ kind: "Born", name: "A" }, { kind: "Moved", name: "B", year: null }], [], "/person/x/").includes("(/person/x/#where)"), true);

/* the timeline */
const ch = S.chaptersOf("**Born.** At Senj. *doc*\n\n**Crossing, 1970.** To Harare. *lore*\n\n**Died.** In Brisbane.");
const st = S.storyOf(ch, S.familyOf(T, "frank", RULE), j, { b: 1951, d: 2026 }, S.ancestryOf(T, "frank", null, RULE));
eq("the stages come in the order a life happens", st.map((s) => s.key), ["origin", "birth", "life", "death", "legacy"]);
eq("the first stop carries the family and is the anchor #family's home", st[0].key, "origin");
eq("the brothers and sisters stand in the birth, the children in what they left behind", [st[1].plabel, st[4].plabel], ["Brothers and sisters", "Children"]);
eq("a living child in the legacy stop is a name, with no dates and no place", st[4].people.map((p) => [p.name, p.dates, p.place, p.href]), [["Greta Fox", "", "", "/person/greta/"]]);
eq("the first stop is always drawn, and says when nobody is named", S.storyOf([], null, [], { b: 1900 }, []).map((s) => [s.key, s.empty]), [["origin", true]]);
eq("a story that is only that sentence is not a story", S.hasStory(S.storyOf([], null, [], { b: 1900 }, [])), false);
eq("a story with a birth chapter is", S.hasStory(S.storyOf(S.chaptersOf("**Born.** At Senj."), null, [], { b: 1900 }, [])), true);
eq("a stage with nothing in it, other than the first, is not drawn", S.storyOf([], null, [], { b: 1900 }, []).length, 1);

/* THE TEST CAN FAIL: plant each fault in a copy of the library and require a check above to catch it. */
const planted = async (label, from, to, mustFail) => {
  const src = fs.readFileSync(path.join(lib, "personstory.js"), "utf8");
  if (!src.includes(from)) { n++; bad++; console.log(`  FAIL  planted fault «${label}»: the text to change is not in the library any more`); return; }
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "story-fault-"));
  fs.copyFileSync(path.join(lib, "person.js"), path.join(dir, "person.js"));
  const f = path.join(dir, "personstory.js");
  fs.writeFileSync(f, src.replace(from, to));
  try {
    const M = await import(pathToFileURL(f).href);
    const g = M.famNode(T, "greta", "Child", "", RULE), h = M.famNode(T, "hal", "Child", "", RULE);
    const caught = {
      "living-dates": g && g.dates !== "", "living-place": g && g.place !== "",
      "held-out": h !== null, "wrong-grand": M.familyOf(T, "eva", RULE).grand.length !== 4,
    }[mustFail];
    n++;
    if (!caught) { bad++; console.log(`  FAIL  planted fault «${label}» was not caught`); }
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
};
await planted("a living relative's dates drawn", "const dates = living ? \"\" :", "const dates = false ? \"\" :", "living-dates");
await planted("a living relative's place drawn", "place: living ? \"\" : q.bp || \"\",", "place: q.bp || \"\",", "living-place");
await planted("a held-out relative drawn", "if (heldOutOf(byId, id, rule)) return null;", "", "held-out");
await planted("the rule not given the parent's life", "const parentLiving = [q.father, q.mother].some((par) => par && byId[par] && isLiving(canon(byId, byId[par]), rule));", "const parentLiving = false;", "held-out");

// the Atlas writes an open span as «(1975–)»; the page says «(from 1975)» so the living-years gate does not take it for a birth
{
  const slice = { places: [{ n: "Testville", cn: "Testland", fl: [[1900, 0]] }], fid: ["testland-flags--era-1900"], flags: [["0 0 1 1", ""]] };
  const eras = { "testland-flags--era-1900": { from: 1900, to: 9999, dates: "1900–present", polity: "Testland", vb: "0 0 1 1", svg: "", pills: [{ t: "Immigration: refugees (1975–)", dot: "#000", tip: "Waves (1945–) and (1975 – )." }], why: "since (1975–)", rep: "" } };
  const c = S.eraFlag(slice, eras, "Testville", 1950);
  eq("an open span in a pill reads (from 1975)", c.pills[0].t, "Immigration: refugees (from 1975)");
  eq("an open span in a pill's tip, spaced or not", c.pills[0].tip, "Waves (from 1945) and (from 1975).");
  eq("an open span in the era's own paragraph", c.why, "since (from 1975)");
}
if (bad) { console.log(`  FAIL  ${bad} of ${n} checks`); process.exit(1); }
console.log(`  ok    ${n} checks — the story layer draws the living as names and leaves the held out unsaid`);
