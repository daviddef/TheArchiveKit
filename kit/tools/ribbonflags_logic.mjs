#!/usr/bin/env node
/* What the mini flags' drawing half (kit/lib/flags.js, used by components/FlagMini.astro) refuses, whatever the data says; and that
   the kit's flag files are the ones index.json lists. The CHOOSING is ribbonflags.py's and the recompute checkribbonflags.py's.
     node kit/tools/ribbonflags_logic.mjs */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { flagsOn, hasFlags, flagClass, flagSrc, livingLine, stripOf, slotClass, FLAG_CAP, FLAG_CREDIT, FLAG_FILE } from "../lib/flags.js";

const KIT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
let fails = 0;
const ok = (name, cond) => { if (!cond) fails++; console.log(`${cond ? "ok  " : "FAIL"} ${name}`); };

const f = (o) => ({ kind: "era", line: "from", place: "Pazin", svg: "austria-flags--era-1804.svg", flag: "austria-flags--era-1804", era: "x--era-1", year: 1850,
  label: "from Pazin, 1850: Habsburg / Austria–Hungary then", grade: "doc", assessed: true, ...o });
const t = (o) => ({ kind: "today", line: "from", place: "Pazin", svg: "croatia-flags--era-1990.svg", flag: "croatia-flags--era-1990", era: "x--era-2", year: null,
  label: "from Pazin: Croatia today", grade: "doc", assessed: true, ...o });
const card = (o) => ({ name: "A", origin: "Pazin", living: false, flags: [f(), t()], ...o });
const kinds = (fl) => fl.map((x) => x.kind).join("+");

ok("a card with no flags draws none", flagsOn({ name: "A" }, "from").length === 0);
ok("era then today, on their line only", kinds(flagsOn(card(), "from")) === "era+today" && flagsOn(card(), "at").length === 0);
ok("today first in the data is still drawn second", kinds(flagsOn(card({ flags: [t(), f()] }), "from")) === "era+today");
ok("no label: the line draws nothing", flagsOn(card({ flags: [f({ label: " " }), t()] }), "from").length === 0);
ok("a file that is not a flag file: nothing", flagsOn(card({ flags: [f({ svg: "../../etc/passwd" })] }), "from").length === 0);
ok("an unknown kind: nothing", flagsOn(card({ flags: [f({ kind: "then" })] }), "from").length === 0);
ok("two era flags on one line: nothing", flagsOn(card({ flags: [f(), f()] }), "from").length === 0);
ok("today's flag with a year: nothing", flagsOn(card({ flags: [f(), t({ year: 2026 })] }), "from").length === 0);
ok("today's flag of the era flag's country is not drawn beside it", kinds(flagsOn(card({ flags: [f(), t({ svg: "austria-flags--era-1955.svg" })] }), "from")) === "era");
ok("today's flag alone", kinds(flagsOn(card({ flags: [t()] }), "from")) === "today");
ok("an era flag on a living card: nothing", flagsOn(card({ living: true }), "from").length === 0);
ok("a living card's today flag: drawn", kinds(flagsOn(card({ living: true, flags: [t()] }), "from")) === "today");
ok("a living card's flag with a year in its words: nothing", flagsOn(card({ living: true, flags: [t({ label: "Croatia, 2026: flag as in Flags Atlas" })] }), "from").length === 0);
ok("a minor is a living line", livingLine({ minor: true }, "from"));
ok("a living spouse's line is a living line, the card's own is not", livingLine({ spouseLiving: true }, "spouse") && !livingLine({ spouseLiving: true }, "from"));
ok("hasFlags", hasFlags([{}, card()]) && !hasFlags([{}, card({ flags: [f({ label: "" })] })]));
ok("the era flag's ring follows the card's evidence; today's says so", flagClass(f({ grade: "inf" })) === "flag-mini flag-mini-inf"
  && flagClass(f({ grade: "x" })) === "flag-mini flag-mini-doc" && flagClass(t()) === "flag-mini flag-mini-doc flag-mini-today");
ok("flagSrc finds the build's url by file name", flagSrc({ "../data/flags/austria-flags--era-1804.svg": "data:x" }, f()) === "data:x" && flagSrc({}, f()) === null);
const sp = (o) => t({ line: "spouse", place: "Senj", label: "spouse of Senj: Croatia today", ...o });
const st = stripOf(card({ flags: [f(), t(), t({ line: "at", label: "at Pazin: Croatia today" }), sp()] }));
ok("the strip draws a flag two places share once, naming both", st.slots.length === 2 && st.slots[1].label === "from Pazin: Croatia today; at Pazin: Croatia today; spouse of Senj: Croatia today");
ok("the strip's order is from, at, spouse, era first", st.slots[0].kind === "era" && st.slots[1].kind === "today");
const many = { name: "M", flags: ["a", "b", "c", "d", "e"].map((x, i) => t({ line: ["from", "at", "spouse"][i % 3], svg: `${x}-flags--era-1.svg`, flag: `${x}-flags--era-1`, label: `${x}` })) };
const sm = stripOf({ ...many, flags: many.flags.filter((x, i) => i < 3) });
ok(`at most ${FLAG_CAP} marks: the rest behind a "+n" whose words list them`, stripOf({ name: "M", flags: [f(), t(), f({ line: "at", svg: "spain-flags--era-1716.svg", flag: "spain-flags--era-1716" }), t({ line: "at", svg: "uruguay-flags--era-1830.svg" }), t({ line: "spouse", svg: "italy-flags--era-1946.svg" })] }).more.length === 2 && sm.more.length === 0);
ok("the evidence ring only on a slot holding the from line's flag", slotClass({ fromLine: true, grade: "inf", kind: "era" }) === "flag-mini flag-mini-inf"
  && slotClass({ fromLine: false, grade: "inf", kind: "era" }) === "flag-mini flag-mini-doc" && slotClass({ fromLine: true, grade: "lore", kind: "today" }) === "flag-mini flag-mini-lore flag-mini-today");
ok("the credit is David's words", FLAG_CREDIT === "Flags: Flags Atlas, by David Defranceski, drawn for this project");

/* the kit's files: every svg listed, every listed drawable flag present, the file names the component accepts */
const dir = path.join(KIT, "data", "flags");
const index = JSON.parse(fs.readFileSync(path.join(dir, "index.json"), "utf8"));
const files = fs.readdirSync(dir).filter((x) => x.endsWith(".svg")).sort();
const listed = Object.values(index.flags).filter((r) => r.file).map((r) => r.file).sort();
ok(`kit/data/flags holds exactly the ${listed.length} drawable flags index.json lists`, JSON.stringify(files) === JSON.stringify(listed));
ok("every flag file name is one FlagMini accepts", files.every((x) => FLAG_FILE.test(x)));
ok("every flag is 300x200 (the 3:2 the style draws)", files.every((x) => fs.readFileSync(path.join(dir, x), "utf8").includes('viewBox="0 0 300 200"')));
ok("index.json carries the credit and claims no open licence", index.credit === FLAG_CREDIT && /no open licence/i.test(index.licence));

console.log(`ribbonflags_logic: ${fails ? fails + " FAILED" : "all ok"}`);
process.exit(fails ? 1 : 0);
