#!/usr/bin/env node
/* Run each component's frontmatter against fixture props and check what it works out.
 *
 * WHY. Thirty-six components and no test between them, which is how these three
 * reached a built page in one afternoon:
 *
 *   · «No name here appears in more than one PEOPLE» — the singular was made by
 *     dropping a trailing s, and «people» has none.
 *   · ev-candidate, ev-method, ev-negative — three classes with no styling in
 *     any theme, because a level was printed straight into a class name. Forty
 *     rows wore the authority of a ladder they were not on.
 *   · A tbody that reserved 9,000px for content the browser was never skipping.
 *
 * The first two are decided in the frontmatter, before any markup exists. So
 * this reads the frontmatter out of the .astro file, hands it fixture props,
 * and reads back what it computed. No Astro, no build, no browser: node alone.
 *
 * WHAT IT CANNOT DO, said plainly so nobody trusts it too far. It does not
 * render. A mistake that lives only in the template — a class spelled one way
 * in the markup and another in the style block — is invisible here, and the
 * third bug above needed a real browser and an off-screen element. This checks
 * the arithmetic and the wording a component decides on before it draws.
 *
 *   node kit/tools/checklogic.mjs [--root <kit dir>]
 */
import fs from "node:fs";
import path from "node:path";

const root = (() => {
  const i = process.argv.indexOf("--root");
  return i > -1 ? process.argv[i + 1] : process.cwd();
})();

function compute(file, props, want) {
  const src = fs.readFileSync(path.join(root, file), "utf8");
  const a = src.indexOf("---");
  const b = src.indexOf("\n---", a + 3);
  if (a !== 0 && a === -1) throw new Error("no frontmatter in " + file);
  const body = src
    .slice(a + 3, b)
    /* the components it draws WITH are not needed: nothing here renders */
    .replace(/^\s*import .*$/gm, "")
    .replace(/Astro\.props/g, "__props");
  const fn = new Function("__props", `${body}\n return { ${want.join(", ")} };`);
  return fn(props);
}

const CASES = [
  /* The bug that shipped: "more than one people". */
  ["EveryName says person, not people", "kit/components/EveryName.astro",
    { names: [], counts: "people" }, ["one", "bearers"],
    (g) => g.one === "person" && g.bearers === true],
  ["EveryName counting records claims no bearers", "kit/components/EveryName.astro",
    { names: [], counts: "records" }, ["one", "bearers"],
    (g) => g.one === "record" && g.bearers === false],
  ["EveryName still answers to the old prop name", "kit/components/EveryName.astro",
    { names: [], unit: "records" }, ["what"], (g) => g.what === "records"],

  /* The evidence ladder leak: a word not among the five must not be graded. */
  ["Timeline grades documented", "kit/components/Timeline.astro",
    { events: [] }, ["graded"], (g) => g.graded("documented") === true],
  ["Timeline refuses to grade a search outcome", "kit/components/Timeline.astro",
    { events: [] }, ["graded"],
    (g) => !g.graded("negative") && !g.graded("candidate") && !g.graded("method")],
  ["Timeline folds an archive's older word", "kit/components/Timeline.astro",
    { events: [] }, ["graded"], (g) => g.graded("lore") && g.graded("doc")],

  /* Grouping granularity: decades for 100 events over 200 years, not for 46
     over 800. Both are real shapes in the estate. */
  ["Timeline groups Booyzen by decade", "kit/components/Timeline.astro",
    { events: Array.from({ length: 103 }, (_, i) => ({ year: 1779 + Math.round(i * 234 / 102), title: "x" })) },
    ["unit"], (g) => g.unit === 10],
  ["Timeline does not group D'Arcy by decade", "kit/components/Timeline.astro",
    { events: Array.from({ length: 46 }, (_, i) => ({ year: 1189 + Math.round(i * 826 / 45), title: "x" })) },
    ["unit"], (g) => g.unit >= 50],
  ["Timeline leaves eighteen rows ungrouped", "kit/components/Timeline.astro",
    { events: Array.from({ length: 18 }, (_, i) => ({ year: 1882 + i, title: "x" })) },
    ["GROUP"], (g) => g.GROUP === false],

  /* A child who did not live five years, read off the dates already printed. */
  ["Households marks a four-day life", "kit/components/Households.astro",
    { rows: [] }, ["short"],
    (g) => g.short({ dates: "11 May 1946 – 15 May 1946" }) === true],
  ["Households marks a three-year life", "kit/components/Households.astro",
    { rows: [] }, ["short"], (g) => g.short({ dates: "1846–1849" }) === true],
  ["Households leaves a full life alone", "kit/components/Households.astro",
    { rows: [] }, ["short"], (g) => g.short({ dates: "1846–1901" }) === false],
  ["Households will not guess from one date", "kit/components/Households.astro",
    { rows: [] }, ["short"],
    (g) => g.short({ dates: "1846" }) === false && g.short({ dates: "b. 1846" }) === false],

  /* Columns and filters appear only where a row has something to put in them. */
  ["Places hides the kind column when nobody has one", "kit/components/Places.astro",
    { rows: [{ name: "a" }, { name: "b" }] }, ["anyKind", "anyN"],
    (g) => g.anyKind === false && g.anyN === false],
  ["Places shows kind and region apart", "kit/components/Places.astro",
    { rows: [{ name: "a", kind: "farm", where: "Cape", n: 3 },
             { name: "b", kind: "church", where: "Natal", n: 1 }] },
    ["anyKind", "kinds", "wheres"],
    (g) => g.anyKind && g.kinds.length === 2 && g.wheres.length === 2],

  /* Corrections filters on two axes, and turns a wall of buttons into a select. */
  ["Corrections offers both axes", "kit/components/Corrections.astro",
    { rows: [{ sev: "major", kind: "Birth year" }, { sev: "minor", kind: "Parentage" }] },
    ["groups"], (g) => g.groups.length === 2],
  ["Corrections offers nothing to choose between one value", "kit/components/Corrections.astro",
    { rows: [{ sev: "major" }, { sev: "major" }] }, ["groups"],
    (g) => g.groups.length === 0],
  ["Corrections keeps 39 kinds out of a button row", "kit/components/Corrections.astro",
    { rows: Array.from({ length: 39 }, (_, i) => ({ kind: "k" + i })) }, ["kinds"],
    (g) => g.kinds.length > 7],

  /* A register row's source is not its kind. */
  ["Register raises a filter for how a record is known", "kit/components/Register.astro",
    { rows: [{ name: "a", surname: "X", kind: "record" }, { name: "b", surname: "X", kind: "family tree" }] },
    ["kinds"], (g) => g.kinds.length === 2],
  ["Register raises none when every row says the same", "kit/components/Register.astro",
    { rows: [{ name: "a", surname: "X", kind: "record" }, { name: "b", surname: "X", kind: "record" }] },
    ["kinds"], (g) => g.kinds.length === 1],
];

let bad = 0, ran = 0;
for (const [name, file, props, want, ok] of CASES) {
  let got, err = null;
  try { got = compute(file, props, want); } catch (e) { err = e; }
  ran++;
  if (err) { bad++; console.log("  BROKE  %s\n         %s", name, err.message); continue; }
  let pass = false;
  try { pass = ok(got); } catch (e) { err = e; }
  if (!pass) {
    bad++;
    console.log("  FAILED %s", name);
    console.log("         it worked out %s", JSON.stringify(got, (k, v) => typeof v === "function" ? "[fn]" : v));
  }
}
console.log("");
console.log(bad
  ? `  FAIL  ${bad} of ${ran} checks`
  : `  ok    ${ran} checks — the wording and the arithmetic components settle before they draw`);
process.exit(bad ? 1 : 0);
