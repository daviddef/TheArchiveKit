// node kit/tools/familyribbon_logic.mjs : the small rules under the family ribbon and the direct-line tint
// (lib/familyribbon.js, lib/directline.js, styles/ours.css), held to the shared example and to arithmetic worked by hand.
//
//   direct line   the file the story makes (the same as kit/tools/directline.py), who is on it, the band's words, a card with no person
//   cards         cards from a lane of lines.json: events are not cards, a living card prints no years, a node with no evidence takes its lane's tier
//   connections   a block per connection in the order of the generations; the family that is not connected says so; the marriages read from the story
//   tint          the tokens in ours.css, both themes: contrast with the ink on the soft fill (4.5:1, 7:1 for --ours-ink), --ours against the page (3:1),
//                 and the hue at least 45 degrees from every evidence colour (accent, dashed gold, dotted grey-brown, thread, glyph)
//   proof         the contrast rule is shown to fail on a tint that would not pass
import fs from "fs"; import path from "path"; import { fileURLToPath } from "url";
import * as D from "../lib/directline.js";
import * as F from "../lib/familyribbon.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const J = (p) => JSON.parse(fs.readFileSync(path.join(kit, p), "utf8"));
let bad = 0;
const eq = (label, got, want) => { const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) { bad++; console.log("  FAIL  " + label + "\n         got  " + JSON.stringify(got) + "\n         want " + JSON.stringify(want)); } else console.log("  ok    " + label); };
const yes = (label, c, detail = "") => { if (!c) { bad++; console.log("  FAIL  " + label + (detail ? "  [" + detail + "]" : "")); } else console.log("  ok    " + label); };

const story = J("data/story-example.json");
const exDl = J("data/direct-line-example.json");
const exFam = J("data/family-lines-example.json");

console.log("the direct line");
const made = D.fromStory(story);
const strip = (d) => ({ people: d.people, partners: d.partners, unlinked: d.unlinked });
eq("fromStory makes the file the example holds", strip(made), strip(exDl));
yes("a person on the line is found", D.isOurs(exDl, "tomas-arden-1790"));
yes("a partner (a spouse who is an ancestor) is found", D.isOurs(exDl, "ilse-arden-nee-brandt-1795") && D.oursOf(exDl, "ilse-arden-nee-brandt-1795").role === "partner");
yes("a namesake is not", !D.isOurs(exDl, "tomas-arden-1791"));
yes("nobody is on a line that is not given", !D.isOurs(null, "tomas-arden-1790"));
eq("the band", D.bandText(D.oursOf(exDl, "pieter-arden-1822"), exDl), "On our direct line · generation 2");
eq("the band uses the archive's noun", D.bandText({ generation: 7 }, { generationLabel: "Gen." }), "On our direct line · Gen. 7");
eq("the band's link", D.storyLink(D.oursOf(exDl, "pieter-arden-1822"), "/story/"), "/story/#ship");
eq("a card with no person is found by its number", D.cardEntry(exDl, story.ribbon.cards[2], 2).generation, 3);
eq("...and keyed gen:N", D.cardKey(story.ribbon.cards[2], 2), "gen:3");
yes("a card with a person that is not on the line is not tinted", D.cardEntry(exDl, { person: "x" }, 0) === null);

console.log("cards from a lane");
const lane = { key: "k", status: "documented", nodes: [
  { place: "Anna", year: "1742", why: "born at Selce", person: "anna-1742", evidence: "read" },
  { place: "Marriage", year: "1885", why: "an event, not a person" },
  { place: "Josip", year: "1857", why: "baptised", person: "/people/josip-1857/", evidence: "indexed" },
  { place: "Milka", year: "1886", why: "", person: "milka-1886" },
  { place: "Ghost", year: "1900", person: "ghost-1900" },
  { place: "Rowan", year: "1999", person: "rowan", evidence: "tree" },
] };
const people = { "anna-1742": { name: "Anna Papić", origin: "Selce" }, "josip-1857": { name: "Josip Papić", years: "1857–1939", spouse: "Antonia Perpić", spouseOrigin: "of Krivi Put", spousePerson: "antonia" }, "milka-1886": { name: "Milka Papić", years: "1886–1971" },
  rowan: { name: "Rowan", living: true, years: "1999–", atPlace: "Senj", atYear: "2020" } };
const r = F.cardsFromLane(lane, people);
eq("an event is not a card, and is counted", r.skipped, 1);
eq("a person nobody described is listed, not guessed", r.unresolved, ["ghost-1900"]);
eq("the cards are the persons in the lane's order", r.cards.map((c) => c.name), ["Anna Papić", "Josip Papić", "Milka Papić", "Rowan"]);
eq("a read node is documented; an indexed one is inferred", [r.cards[0].originGrade, r.cards[1].originGrade], ["doc", "inf"]);
eq("a node with no evidence takes its lane's tier", r.cards[2].originGrade, "doc");
eq("a tree node is family lore", r.cards[3].originGrade, "lore");
eq("a living card prints no years and no at-year", [r.cards[3].years, r.cards[3].atYear], ["", ""]);
eq("a person page given as a path is a slug", r.cards[1].person, "josip-1857");
eq("every card has every field", r.cards.every((c) => F.CARD_FIELDS.every((k) => k in c)), true);
eq("a family lore lane makes lore cards", F.cardsFromLane({ status: "family-lore", nodes: [{ person: "a" }] }, { a: { name: "A" } }).cards[0].originGrade, "lore");
eq("findLane finds a lane in a set", F.findLane({ sets: [{ slug: "papic", lanes: [{ key: "senj" }] }] }, { set: "papic", key: "senj" }).key, "senj");
eq("...and not in another set", F.findLane({ sets: [{ slug: "papic", lanes: [{ key: "senj" }] }] }, { set: "x", key: "senj" }), null);

console.log("the connections");
const brandt = exFam.families[0], harrow = exFam.families[1];
const blocks = F.blocksOf(brandt, exDl);
eq("a block for each connection, in the order of the generations", blocks.map((b) => [b.ourGeneration, b.word, b.theirName]), [[1, "married", "Ilse Brandt"], [2, "son of", "Ilse Brandt"]]);
eq("the generation is the direct-line file's, whatever the family says", F.blocksOf({ cards: [], connections: [{ ourSlug: "pieter-arden-1822", ourGeneration: 9, theirSlug: "x", theirName: "X", relation: "son of", grade: "doc", storyHref: "" }] }, exDl)[0].ourGeneration, 2);
eq("our name comes from the direct-line file", blocks[0].ourName, "Tomas Arden");
eq("a family the line does not touch gets one quiet block with the reason", F.blocksOf(harrow, exDl).map((b) => [b.kind, b.why.slice(0, 10)]), [["none", "A Harrow b"]]);
eq("...and with no reason it still says so", F.blocksOf({ cards: [] }, exDl)[0].kind, "none");
eq("a block as a sentence", F.blockSentence(blocks[0]), "Our line, generation 1: Tomas Arden married Ilse Brandt, of Hollin (documented)");
eq("the not-connected sentence", F.blockSentence({ kind: "none", why: "no marriage yet" }), "Not connected to our line yet: no marriage yet");
eq("which cards a connection touches", [...F.joinsOf(brandt)], [["ilse-arden-nee-brandt-1795", [1, 2]]]);
eq("a relation is worded", [F.relationWord("daughter of"), F.relationWord("godparent of")], ["daughter of", "godparent of"]);
yes("a godparent needs a document", F.RELATIONS["godparent of"].needsDoc && !F.RELATIONS.married.needsDoc);
const marr = F.marriageConnections(story.ribbon, (s) => (s === "ilse-arden-nee-brandt-1795" ? "brandt" : null));
eq("the story's marriages, for the family that owns the spouse", Object.keys(marr), ["brandt"]);
eq("...with the card's own grade, the weakest it admits", [marr.brandt[0].relation, marr.brandt[0].grade, marr.brandt[0].ourGeneration, marr.brandt[0].storyHref], ["married", "doc", 1, "/story/#weaver"]);
eq("a spouse the archive cannot place is left out", Object.keys(F.marriageConnections(story.ribbon, () => null)), []);
eq("a connection the family states wins over the derived one", F.mergeConnections([{ ourSlug: "a", theirSlug: "b", ourGeneration: 2, grade: "doc" }], [{ ourSlug: "a", theirSlug: "b", ourGeneration: 2, grade: "lore" }, { ourSlug: "c", theirSlug: "d", ourGeneration: 1 }]).map((c) => c.grade || "derived"), ["derived", "doc"]);
eq("the status line is the lines page's", F.familyStatus({ status: "inferred", statusNote: "Hollin", span: [1818, null] }).text, "Documented from 1818 · Hollin");
eq("a living card's years are not printed, whatever the data holds", F.cardYears({ living: true, years: "1990–" }), "");

console.log("the tint (styles/ours.css)");
const css = fs.readFileSync(path.join(kit, "styles/ours.css"), "utf8");
const story_css = fs.readFileSync(path.join(kit, "styles/story.css"), "utf8");
const tok = (src, name, block) => { const m = new RegExp(`${block}[^}]*?${name}:\\s*(#[0-9a-fA-F]{6})`, "s").exec(src); return m && m[1]; };
const lum = (hex) => { const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const hue = (hex) => { const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255); const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; if (!d) return 0; const h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return (h * 60 + 360) % 360; };
const dh = (a, b) => { const d = Math.abs(hue(a) - hue(b)) % 360; return d > 180 ? 360 - d : d; };
// the story's own fallbacks (the colours the story draws with when the archive sets none): [theme][name]
const themes = {
  light: { block: ":where\\(:root\\) \\{", ours: null, ink: ["#1f1d1a", "#46423b", "#6b665e"], page: "#ffffff", evid: ["#7a2e1f", "#7a5200", "#5f584a", "#a8442b", "#845c15"] },
  dark: { block: ":where\\(:root\\[data-theme=\"dark\"\\]\\) \\{", ink: ["#ece8e1", "#cfc9bf", "#a39d91"], page: "#17212a", evid: ["#d98b72", "#e0b45c", "#b0a796", "#d97a5f", "#d2a24a"] },
};
for (const [name, T] of Object.entries(themes)) {
  const ours = tok(css, "--ours", T.block), soft = tok(css, "--ours-soft", T.block), oi = tok(css, "--ours-ink", T.block);
  yes(`${name}: the three tokens are defined`, ours && soft && oi, `${ours} ${soft} ${oi}`);
  if (!(ours && soft && oi)) continue;
  T.ink.forEach((c, i) => yes(`${name}: ${["ink", "ink-2", "ink-3"][i]} reads on --ours-soft at 4.5:1 or better (${ratio(c, soft).toFixed(1)})`, ratio(c, soft) >= 4.5));
  yes(`${name}: --ours-ink reads on --ours-soft at 7:1 or better (${ratio(oi, soft).toFixed(1)})`, ratio(oi, soft) >= 7);
  yes(`${name}: --ours reads against the page at 3:1 or better (${ratio(ours, T.page).toFixed(1)})`, ratio(ours, T.page) >= 3);
  yes(`${name}: --ours-soft is a tint, not the page (${ratio(soft, T.page).toFixed(2)})`, ratio(soft, T.page) >= 1.05 && ratio(soft, T.page) < 3);
  const near = T.evid.filter((e) => dh(ours, e) < 45);
  yes(`${name}: the hue is 45 degrees or more from every evidence colour (${Math.round(hue(ours))} against ${T.evid.map((e) => Math.round(hue(e))).join(", ")})`, near.length === 0, near.join(","));
}
yes("story.css still defines the fallbacks this test assumes", ["#7a2e1f", "#7a5200", "#5f584a", "#a8442b", "#845c15", "#d98b72", "#e0b45c"].every((c) => story_css.toLowerCase().includes(c)));
yes("every rule in ours.css that sets the root tokens is :where() (an archive's own value wins)", !/^:root\s*\{[^}]*--ours/m.test(css));
console.log("proof: the rules fail on a tint that would not pass");
yes("contrast: a pale yellow-grey fails the ink rule", ratio("#6b665e", "#cfc9a0") < 4.5);
yes("hue: a terracotta tint is refused", dh("#c0583a", "#a8442b") < 45);

console.log(bad ? `\nfamilyribbon_logic: ${bad} FAILED` : "\nfamilyribbon_logic: all ok");
process.exit(bad ? 1 : 0);
