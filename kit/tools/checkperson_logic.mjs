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
import path from "node:path";
import { pathToFileURL } from "node:url";
const i = process.argv.indexOf("--root");
const root = i > 0 ? path.resolve(process.argv[i + 1]) : path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const L = await import(pathToFileURL(path.join(root, "kit", "lib", "person.js")).href);
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
eq("an index entry has NO suggested grade (owner decision)", L.GRADE_HINT.indexed, null);

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

/* living: strict > 80, flags, and «b = living» (a birth field that says so, with no boolean anywhere) */
eq("born 81 years ago is presumed dead", L.isLiving({ born: 1945 }, { now: 2026 }), false);
eq("born exactly 80 years ago is presumed alive (strict >)", L.isLiving({ born: 1946 }, { now: 2026 }), true);
eq("a death settles it", L.isLiving({ born: 1990, died: 2020 }, { now: 2026 }), false);
eq("a flag settles it", L.isLiving({ living: true, born: 1700 }, { now: 2026 }), true);
eq("presumedLiving counts", L.isLiving({ presumedLiving: true }), true);
eq("born = 'living' is a statement, not a date", L.isLiving({ born: "living" }), true);
eq("no dates, no flag: not guessed alive", L.isLiving({ name: "x" }), false);
eq("living person yields NO structured data", L.personAbout({ name: "x", born: 1990, living: true }), null);
eq("dead person yields iso dates", L.personAbout({ name: "x", born: "13 Dec 1854", died: "1920" }, { now: 2026 }).birthDate, "1854-12-13");
eq("circa birth is not asserted as an exact date", L.personAbout({ name: "x", born: "c. 1854", died: 1920 }, { now: 2026 }).birthDate, undefined);

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
eq("empty chart says why", L.chartEmptyReason({ relations: {} }), "none-recorded");
eq("empty chart with a name page says it is name-level", L.chartEmptyReason({ relations: {} }, { nameHref: "/who/x/" }), "name-level");
eq("all-living relatives is its own reason", L.chartEmptyReason({ relations: { parents: [{ living: true }] } }), "living-withheld");
eq("a drawn relative means no empty reason", L.chartEmptyReason({ relations: { parents: [{ name: "a" }] } }), null);

/* the head of the page */
const mk = L.personMeta({ name: "Severa FERNANDEZ (m. Alejandro LERENA the younger, 1854)", born: 1830, died: 1900 }, { siteName: "The Lerena Archive", now: 2026 });
eq("title carries the lifespan and the site, not the qualifier", mk.title, "Severa Fernandez, 1830\u20131900 \u2014 The Lerena Archive");
eq("qualifier is returned separately, in the same style as the name", mk.qualifier, "m. Alejandro Lerena the younger, 1854");
eq("a dead person is indexable", mk.noindex, false);
const lv = L.personMeta({ name: "Some NAME", born: 1990, living: true }, { siteName: "S", now: 2026 });
eq("a living person is noindex", lv.noindex, true);
eq("a living person's title has no dates", lv.title, "Some Name \u2014 S");
eq("a living person's description is the fixed sentence", lv.description, L.LIVING_SENTENCE);
eq("a living person has no structured data", lv.about, null);
if (bad) { console.log(`  FAIL  ${bad} of ${n} checks`); process.exit(1); }
console.log(`  ok    ${n} checks — the dates, the words and the living rule a people page settles before it draws`);
