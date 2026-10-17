#!/usr/bin/env node
/* Does kit/lib/person.js still decide what the people-page spec says it decides?
 *
 * The library is pure, so this imports it and asks it things. No Astro, no build.
 * Every case is a question with one right answer written down BEFORE the code
 * answered it, and several are the shape of a fault the estate has actually had:
 * an unlabelled date read as a birth, an unknown source word promoted to a kind
 * one, a living person given a birth date in structured data.
 *
 *   node kit/tools/checkperson_logic.mjs [--root <kit dir>]
 *
 * Exit 0 all hold, 1 any fails. Prints «ok    N checks».
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
const i = process.argv.indexOf("--root");
const root = i > 0 ? path.resolve(process.argv[i + 1]) : path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const PERSON_JS = path.join(root, "kit", "lib", "person.js");
const L = await import(pathToFileURL(PERSON_JS).href);
const FIXTURE = JSON.parse(fs.readFileSync(path.join(root, "kit", "data", "living-rule-cases.json"), "utf8"));
const SOURCES_JSON = JSON.parse(fs.readFileSync(path.join(root, "kit", "data", "public-sources.json"), "utf8"));
let n = 0, bad = 0;
const eq = (name, got, want) => {
  n++; const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) { bad++; console.log(`  FAILED ${name}\n         got  ${JSON.stringify(got)}\n         want ${JSON.stringify(want)}`); }
};

/* sections: the order and the headings are the contract */
eq("section order", L.PERSON_SECTIONS.map((s) => s.id), ["family","record","sources","namesakes","media","notes"]);
eq("required sections", L.PERSON_SECTIONS.filter((s) => s.required).map((s) => s.id), ["family","record","sources"]);

/* sources: every older word lands on one; unknown is VISIBLE, never a kind default */
for (const [w, want] of [["register","read"],["a record read here","read"],["doc","read"],["index","indexed"],["Indexed","indexed"],
  ["lore","tree"],["Testimony","tree"],["family tree","tree"],["inf","inferred"],["best candidate","inferred"],["", "none"],["named here only","none"],["dis","disputed"]])
  eq(`source ${JSON.stringify(w)}`, L.readSource(w).source, want);
eq("unknown source word is unmarked, not 'read' and not 'tree'", L.readSource("strong"), { source: "unmarked", line: false, known: false });
eq("'line' is a flag, not a source", L.readSource("line"), { source: "none", line: true, known: true });
eq("unmarked has no grade hint", L.GRADE_HINT.unmarked, null);
eq("an index entry has NO suggested grade (ruled 16 Oct 2026: it stays ungraded)", L.GRADE_HINT.indexed, null);
eq("an image held has NO suggested grade (ruled)", L.GRADE_HINT.scanned, null);
eq("no grade may be drawn beside an index entry", L.gradeAllowed("indexed"), false);
eq("no grade may be drawn beside an image held", L.gradeAllowed("scanned"), false);
eq("a grade may be drawn beside a record read", L.gradeAllowed("read"), true);
eq("two axes: five grades", L.GRADES, ["documented","probable","inferred","family","disputed"]);
eq("two axes: seven source words, each with a label and a class", L.SOURCE_KEYS.every((k) => L.SOURCES[k] && L.SOURCES[k].label && L.SOURCES[k].cls) && L.SOURCE_KEYS.length, 7);
eq("the direct line is never a grade", L.GRADES.includes("line"), false);

/* dates */
for (const [raw, want] of [["13 Dec 1854","13 Dec 1854"],["13 December 1854","13 Dec 1854"],["Dec 13 1854","13 Dec 1854"],["Dec 13, 1854","13 Dec 1854"],
  ["5 JUL 1767","5 Jul 1767"],["1876-10-01","1 Oct 1876"],["1950-Mar-19","19 Mar 1950"],["13/12/1854","13 Dec 1854"],["c. 1854","c. 1854"],["1854","1854"],["March 1854","Mar 1854"]])
  eq(`date ${raw}`, L.fmtDate(raw, "short").text, want);
eq("long style", L.fmtDate("13 Dec 1854", "long").text, "13 December 1854");
eq("d/m/y is read day-first (estate order)", L.parseDate("03/04/1900"), { y: 1900, m: 3, d: 3, circa: false, ok: true });
eq("garbage is returned as written and flagged, not guessed", L.fmtDate("the winter of the big snow"), { text: "the winter of the big snow", ok: false });
eq("'living' in a date field is not a date", L.fmtDate("living").empty, true);
eq("lifespan range uses an en dash, no spaces", L.lifespan("13 Dec 1854", "2 Jan 1920"), "1854–1920");
eq("a single date is always labelled (born)", L.lifespan("1854", ""), "b. 1854");
eq("a single date is always labelled (died)", L.lifespan("", "1920"), "d. 1920");
eq("no dates, no string", L.lifespan("", ""), "");
eq("full dates in the header line", L.lifespan("13 Dec 1854", "2 Jan 1920", { years: false }), "13 Dec 1854–2 Jan 1920");

/* living: the standard (version 2). The shared cases are asserted below; these are the
   person-level mappings on top of them. */
const SRC = SOURCES_JSON;
const N26 = { now: 2026, sources: SRC };
eq("born 81 years ago is not living", L.isLiving({ born: 1945 }, N26), false);
eq("born exactly 80 years ago is living", L.isLiving({ born: 1946 }, N26), true);
eq("a recorded death settles it", L.isLiving({ born: 1990, died: 2020 }, N26), false);
eq("an UNDATED death settles it (dead: true)", L.isLiving({ born: 1990, dead: true }, N26), false);
eq("a recorded burial settles it", L.isLiving({ born: 1990, buried: "St Mary's" }, N26), false);
eq("a death place implies a death", L.isLiving({ born: 1990, deathPlace: "Testville" }, N26), false);
eq("died = 'living' is not a death", L.isLiving({ born: 1990, died: "living" }, N26), true);
eq("a public source settles it", L.isLiving({ born: 1990, citations: ["FamilySearch"] }, N26), false);
eq("a source object with a provider counts", L.isLiving({ born: 1990, sources: [{ provider: "Findmypast", title: "1939 Register" }] }, N26), false);
eq("a private tree entry does not", L.isLiving({ born: 1990, sources: ["MyHeritage family tree entry"] }, N26), true);
eq("a hand-set living:true is NOT read (no dates, not living)", L.isLiving({ name: "x", living: true }, N26), false);
eq("a hand-set presumedLiving is NOT read", L.isLiving({ name: "x", presumedLiving: true }, N26), false);
eq("a hand-set living:false does not make a living person dead", L.isLiving({ born: 1990, living: false }, N26), true);
eq("born = 'living' with no year is not living (no birth year)", L.isLiving({ born: "living" }, N26), false);
eq("no dates, no flag: not living", L.isLiving({ name: "x" }, N26), false);
eq("a known child is living (David 16 Oct 2026)", L.isLiving({ born: 2015 }, N26), true);
eq("a known child is not held out", L.isHeldOut({ born: 2015 }, { ...N26, parentLiving: true }), false);
eq("an undated person with a living parent is held out", L.isHeldOut({ name: "x" }, { ...N26, parentLiving: true }), true);
eq("the row's own parentLiving counts", L.isHeldOut({ name: "x", parentLiving: true }, N26), true);
eq("held by id", L.isHeldOut({ id: "7", born: 1700, died: 1760 }, { ...N26, heldIds: ["7"] }), true);
eq("citations without a source list THROW, not guess", (() => { try { L.isLiving({ born: 1990, citations: ["Some Archive"] }, { now: 2026 }); return "no throw"; } catch (e) { return "throws"; } })(), "throws");
eq("FamilySearch needs no list", L.isLiving({ born: 1990, citations: ["FamilySearch"] }, { now: 2026 }), false);
eq("living person yields NO structured data", L.personAbout({ name: "x", born: 1990 }, N26), null);
eq("dead person yields iso dates", L.personAbout({ name: "x", born: "13 Dec 1854", died: "1920" }, N26).birthDate, "1854-12-13");
eq("circa birth is not asserted as an exact date", L.personAbout({ name: "x", born: "c. 1854", died: 1920 }, N26).birthDate, undefined);

/* a living person's place: town and country, never an address or an institution */
eq("town and country as given", L.livingPlace({ town: "Testville", country: "Nowhere" }), { text: "Testville, Nowhere", refused: false });
eq("a single place string is accepted as written", L.livingPlace({ place: "Testville, Nowhere" }), { text: "Testville, Nowhere", refused: false });
eq("an address-like place is REFUSED, not shown", L.livingPlace({ place: "1 Test Street, Testville, Nowhere" }), { text: "", refused: true });
eq("an institution is refused", L.livingPlace({ town: "Testville Hospital", country: "Nowhere" }), { text: "", refused: true });
eq("no place, nothing", L.livingPlace({}), { text: "", refused: false });

/* relations a page may publish */
const kin = { relations: { children: [{ name: "undated" }, { name: "dated", born: 2015 }, { name: "dead-undated", died: 1799 }], parents: [{ name: "p", gap: true }, { name: "q" }], siblings: [{ name: "s", heldOut: true }] } };
const pr = L.publishedRelations({ born: 1990, ...kin }, N26);
eq("a living person's undated child is held out; a dated one and a dead one stay", pr.children.map((r) => r.name), ["dated", "dead-undated"]);
eq("the old «withheld» placeholder is dropped, not drawn", pr.parents.map((r) => r.name), ["q"]);
eq("a row flagged heldOut is dropped", pr.siblings.length, 0);
const pd = L.publishedRelations({ born: 1700, died: 1760, ...kin }, N26);
eq("a dead person's undated child is not held out", pd.children.map((r) => r.name), ["undated", "dated", "dead-undated"]);

/* THE SHARED CASES: the same file living_rule_selftest.py asserts against living_rule.py */
const answers = (rule, c) => {
  const i = c.in, cit = i.citations || [], y = FIXTURE.today;
  return {
    public_source: rule.publicSource(cit, SOURCES_JSON),
    is_living: rule.isLiving(i.birth_year ?? null, i.recorded_dead || false, cit, y, SOURCES_JSON, i.youngest_child_year ?? null, i.said_living || false),
    possible_minor: rule.possibleMinor(i.birth_year ?? null, i.recorded_dead || false, cit, i.parent_living || false, y, SOURCES_JSON, i.youngest_child_year ?? null, i.said_living || false),
    is_held_out: rule.isHeldOut(i.id ?? "none", i.birth_year ?? null, i.recorded_dead || false, cit, i.parent_living || false, i.held_ids || [], y, SOURCES_JSON, i.youngest_child_year ?? null, i.said_living || false),
  };
};
const sharedFailures = (rule, address) => {
  const out = [];
  for (const c of FIXTURE.cases) {
    const got = answers(rule, c);
    for (const [k, v] of Object.entries(c.want)) if (got[k] !== v) out.push(`${c.id}: ${k} got ${got[k]} want ${v}`);
  }
  for (const pc of FIXTURE.place_cases) if (address(pc.place) !== pc.address_like) out.push(`place ${pc.place}: got ${address(pc.place)}`);
  return out;
};
const ids = FIXTURE.cases.map((c) => c.id);
eq("fixture: case ids are unique", new Set(ids).size, ids.length);
const tags = new Set(FIXTURE.cases.flatMap((c) => c.tags));
eq("fixture: every required scenario has a case", FIXTURE.required_tags.filter((t) => !tags.has(t)), []);
eq("fixture: at least 25 rule cases and 10 place cases", FIXTURE.cases.length >= 25 && FIXTURE.place_cases.length >= 10, true);
eq(`shared cases: all ${FIXTURE.cases.length} rule and ${FIXTURE.place_cases.length} place cases agree with living_rule.py's answers`, sharedFailures(L.livingRule, L.placeIsAddressLike), []);

/* THE TEST CAN FAIL: plant the fault in a COPY of person.js (the real one is never touched)
   and require the shared cases to catch it. person.js imports nothing, so one file is a copy. */
const plant = (from, to) => {
  const src = fs.readFileSync(PERSON_JS, "utf8");
  if (!src.includes(from)) return { missing: true };
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "person-fault-"));
  const f = path.join(dir, "person.mjs");
  fs.writeFileSync(f, src.replace(from, to));
  return import(pathToFileURL(f).href).then((M) => ({ fails: sharedFailures(M.livingRule, M.placeIsAddressLike) })).finally(() => fs.rmSync(dir, { recursive: true, force: true }));
};
for (const [label, from, to, must] of [
  ["a 100-year bound", "LIVING_YEARS = 80;", "LIVING_YEARS = 100;", "age-81-is-not-living"],
  ["a 79-year bound", "LIVING_YEARS = 80;", "LIVING_YEARS = 79;", "age-80-is-living"],
  ["a strict < instead of <=", "<= LIVING_YEARS", "< LIVING_YEARS", "age-80-is-living"],
  ["a recorded death ignored", "    if (recordedDead) return false;\n    if (publicSource(citations, sources)) return false;\n    if (birthYear == null)", "    if (publicSource(citations, sources)) return false;\n    if (birthYear == null)", "recorded-death-means-dead"],
  ["a known child held out", "    if (birthYear != null) return false;\n    if (livingRule.recentChild(youngestChildYear, todayYear)) return false;\n    if (saidLiving) return false;   /* the archive's own data says living: a known child follows the standard */\n    return Boolean(parentLiving);", "    return Boolean(parentLiving);", "known-child-is-living-and-not-held-out"],
  ["a 100-year recent-child bound", "CHILD_LIVING_YEARS = 60;", "CHILD_LIVING_YEARS = 100;", "undated-child-boundary-61"],
  ["a 59-year recent-child bound", "CHILD_LIVING_YEARS = 60;", "CHILD_LIVING_YEARS = 59;", "undated-child-boundary-60"],
  ["the recent child ignored", "return Boolean(saidLiving) || livingRule.recentChild(youngestChildYear, todayYear);", "return Boolean(saidLiving);", "undated-recent-child"],
  ["a living statement ignored by possibleMinor", "    if (saidLiving) return false;   /* the archive's own data says living: a known child follows the standard */\n", "", "said-living-child-of-living-parent-not-held-out"],
  ["a living statement ignored", "return Boolean(saidLiving) || livingRule.recentChild(youngestChildYear, todayYear);", "return livingRule.recentChild(youngestChildYear, todayYear);", "said-living-undated"],
  ["a parent of a recent child still held out", "    if (livingRule.recentChild(youngestChildYear, todayYear)) return false;\n    if (saidLiving) return false;   /* the archive's own data says living: a known child follows the standard */\n    return Boolean(parentLiving);", "    if (saidLiving) return false;   /* the archive's own data says living: a known child follows the standard */\n    return Boolean(parentLiving);", "undated-living-parent-and-recent-child"],
]) {
  const r = await plant(from, to);
  eq(`planted fault (${label}) is caught by the shared cases`, !r.missing && r.fails.some((f) => f.startsWith(must)), true);
}

/* the checker's vocabulary (a Python file that reads built HTML) must say the same seven words */
const checkerSrc = fs.readFileSync(path.join(root, "kit", "tools", "checkperson.py"), "utf8");
eq("checkperson.py knows exactly the library's seven source words", L.SOURCE_KEYS.filter((k) => !checkerSrc.includes(JSON.stringify(L.SOURCES[k].label))), []);
eq("checkperson.py knows the five grade words", L.GRADES.filter((g) => !checkerSrc.includes(g[0].toUpperCase() + g.slice(1))), []);

/* names */
eq("title-case a capitalised surname", L.displayName("Severa FERNANDEZ"), "Severa Fernandez");
eq("particle stays lower", L.displayName("Juan DE LA CRUZ"), "Juan de la Cruz");
eq("apostrophe form", L.displayName("Mary D'ARCY"), "Mary D'Arcy");
eq("already mixed case is untouched", L.displayName("Maria Rosa Melluso"), "Maria Rosa Melluso");
eq("diacritics survive", L.displayName("Ivan BLAŽEVIĆ"), "Ivan Blažević");
eq("asRecorded keeps capitals (decision 4 option)", L.displayName("Severa FERNANDEZ", { style: "asRecorded" }), "Severa FERNANDEZ");
eq("an initial is not lower-cased", L.displayName("J. SMITH"), "J. Smith");
eq("qualifier leaves the h1", L.splitQualifier("Severa FERNANDEZ (m. Alejandro LERENA the younger, 1854)"), { name: "Severa FERNANDEZ", qualifier: "m. Alejandro LERENA the younger, 1854" });
eq("no qualifier", L.splitQualifier("Maria Rosa"), { name: "Maria Rosa", qualifier: "" });

/* stubs and empty charts */
eq("name-only is a stub", L.stubReason({ name: "x", events: [], sources: [], relations: {} }), "name-only");
eq("a person with an event is not a stub", L.stubReason({ events: [{}], sources: [], relations: {} }), null);
eq("empty chart says why", L.chartEmptyReason({ relations: {} }, N26), "none-recorded");
eq("empty chart with a name page says it is name-level", L.chartEmptyReason({ relations: {} }, { ...N26, nameHref: "/who/x/" }), "name-level");
eq("living relatives are drawn, so a chart of them is not empty", L.chartEmptyReason({ born: 1700, died: 1760, relations: { parents: [{ name: "a", born: 1990 }] } }, N26), null);
eq("a chart whose only relatives are held out is empty, and says nothing of them", L.chartEmptyReason({ born: 1990, relations: { children: [{ name: "undated" }], parents: [{ name: "w", gap: true }] } }, N26), "none-recorded");
eq("the old living-withheld reason is gone", Object.keys(L.EMPTY_TEXT).includes("living-withheld"), false);
eq("a drawn relative means no empty reason", L.chartEmptyReason({ relations: { parents: [{ name: "a" }] } }, N26), null);

/* the head of the page */
const mk = L.personMeta({ name: "Severa FERNANDEZ (m. Alejandro LERENA the younger, 1854)", born: 1830, died: 1900 }, { siteName: "The Lerena Archive", now: 2026, sources: SRC });
eq("title carries the lifespan and the site, not the qualifier", mk.title, "Severa Fernandez, 1830\u20131900 \u2014 The Lerena Archive");
eq("qualifier is returned separately, in the same style as the name", mk.qualifier, "m. Alejandro Lerena the younger, 1854");
eq("a dead person is indexable", mk.noindex, false);
const lv = L.personMeta({ name: "Some NAME (m. Another NAME, 1799)", born: 1990 }, { siteName: "S", now: 2026, sources: SRC });
eq("a living person's qualifier is dropped (it can hold a spouse and a year)", lv.qualifier, "");
eq("a living person is noindex", lv.noindex, true);
eq("a living person's title has no dates", lv.title, "Some Name \u2014 S");
eq("a living person's description is the fixed sentence", lv.description, L.LIVING_SENTENCE);
eq("the fixed sentence is the standard's wording", L.LIVING_SENTENCE, "A living person (80 or younger, with no death recorded) is named with their relationships and their town and country, and nothing more.");
eq("a living person has no structured data", lv.about, null);
if (bad) { console.log(`  FAIL  ${bad} of ${n} checks`); process.exit(1); }
console.log(`  ok    ${n} checks — the dates, the words and the living rule a people page settles before it draws`);
