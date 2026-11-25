// node kit/tools/corrections_logic.mjs : what the Corrections page and /whats-new/ must agree on (lib/corrections.js): one stable anchor per correction
// row, the same on both sides, and the page's newest-first order. Cases are written from the shapes the archives keep corrections in.
import { corrIdMap, byDateDesc, factsOf, kindBefore, toneOf, cardOf, heartbeat, kindFilterable, longDate, TONE_ORDER } from "../lib/corrections.js";
import { bookIndex, linkBooks, bookKind, bookYears } from "../lib/booklinks.js";
import { placeIndex, linkPlaces, yearAround, flagsFor } from "../lib/placelinks.js";
import { nameIndex, linkNames } from "../lib/namelinks.js";
import { buildPulse } from "../lib/pulse.js";
let bad = 0;
const ok = (label, cond, detail) => { if (!cond) { bad++; console.log("  FAIL  " + label + (detail ? "\n         " + detail : "")); } else console.log("  ok    " + label); };

const rows = [
  { when: "16 Oct 2026", what: "A burial placed at Pula", sev: "minor" },
  { when: "17 Nov 2026", what: "Two emigrants of 1905 placed at 'Italy' or nowhere", sev: "serious" },
  { when: "17 Nov 2026", what: "Two emigrants of 1905 placed at 'Italy' or nowhere", sev: "serious" },
  { when: "2026-11-09", what: "A birth year of 1833", sev: "minor" },
  { what: "An undated one" },
];
const ids = corrIdMap(rows);
ok("one id per row", ids.size === 5 && new Set([...ids.values()]).size === 5);
ok("the id starts with the day", ids.get(rows[1]).startsWith("c-2026-11-17-") && ids.get(rows[3]).startsWith("c-2026-11-09-") && ids.get(rows[4]).startsWith("c-undated-"));
ok("a repeated day and headline gets -2, in file order", ids.get(rows[2]) === ids.get(rows[1]) + "-2");
ok("ids do not change when the rows are rebuilt", [...corrIdMap(rows.map((r) => ({ ...r }))).values()].join() === [...ids.values()].join());
ok("ids are safe in a URL fragment", [...ids.values()].every((v) => /^c-[a-z0-9-]+$/.test(v)));

const sorted = byDateDesc(rows);
ok("newest first", sorted[0] === rows[1] && sorted[1] === rows[2] && sorted[2] === rows[3] && sorted[3] === rows[0]);
ok("an undated row goes last", sorted[4] === rows[4]);
const sev = [{ when: "5 Nov 2026", what: "a", sev: "serious" }, { when: "5 Nov 2026", what: "b", sev: "minor" }];
ok("rows on one day keep the archive's order", byDateDesc(sev)[0] === sev[0] && byDateDesc(sev)[1] === sev[1]);
const none = [{ when: "1814", what: "x" }, { when: "", what: "y" }];
ok("nothing dated: the order is untouched", byDateDesc(none).join() === none.join());
ok("a month alone sorts with its month", byDateDesc([{ when: "Sept 2026", what: "m" }, { when: "2026-10-02", what: "d" }])[0].what === "d");

/* the pulse links each correction to the same anchor, and carries who it is about */
const cor = [{ when: "11 Nov 2026", what: "A man placed at Bakar", for: [["/people/anna/", "Anna Bakar"], ["//evil/", "no"], ["/people/anna/", "Anna Bakar"]] }, { when: "11 Nov 2026", what: "Another" }];
const p = buildPulse({ searched: [], corrections: cor, today: "2026-11-11", correctionsHref: "/corrections/" });
const m = corrIdMap(cor);
const c0 = p.days[0].corrections.find((e) => e.head.startsWith("A man"));
ok("a What's new card links to its own entry", c0 && c0.href === "/corrections/#" + m.get(cor[0]), c0 && c0.href);
ok("the card names who it is about (own pages only, once each)", c0 && c0.people.list.length === 1 && c0.people.list[0][1] === "Anna Bakar");
ok("a correction with no `for` names nobody", p.days[0].corrections.find((e) => e.head === "Another").people.list.length === 0);
ok("the header panel's card links the same anchor", p.cards.some((c) => c.type === "corrected" && c.href === "/corrections/#" + m.get(cor[0])));

/* who, where, when and which record: read out of the archive's own rendered sentences, nothing invented */
const f = factsOf('<p>The weddings are of <strong>1 February 1858</strong> (the bride is <a href="/person/maria-voinich/">Maria Voinić</a>), on <a href="/places/medulin/">the Medulin page</a>; <a class="lk-rec" href="https://www.familysearch.org/ark:/61903/3:1:3QSQ-G99X-G4G6" title="FamilySearch image 3:1:3QSQ-G99X-G4G6"><code>3:1:3QSQ</code></a>; born 1828 and 1831, read on 16 November 2026.</p>');
ok("a linked person is a person chip", f.people.length === 1 && f.people[0].name === "Maria Voinić" && f.people[0].href === "/person/maria-voinich/");
ok("a linked place is a place chip", f.places.length === 1 && f.places[0].href === "/places/medulin/");
ok("a record link is a source, labelled by its title", f.sources.length === 1 && f.sources[0].name === "FamilySearch image 3:1:3QSQ-G99X-G4G6");
ok("dates: the full date, the bare years, not the work date", f.dates.map((d) => d.text).join("|") === "1 February 1858|1828|1831", f.dates.map((d) => d.text).join("|"));
ok("a year inside a longer date is not shown twice", !f.dates.some((d) => d.text === "1858"));
ok("died / buried is a death, born / baptised a birth, married a marriage", kindBefore("who died on ") === "death" && kindBefore("was buried at Pula on ") === "death" && kindBefore("born ") === "birth" && kindBefore("baptised at Omiš on ") === "birth" && kindBefore("they married in ") === "marriage");
ok("danger of death is not a death", kindBefore("the twin was baptised in danger of death on ") === "birth");
ok("a baptism BOOK is not a birth", kindBefore("the baptism book of ") === "" && factsOf("<p>the baptism book 1764–1791</p>").dates.every((d) => !d.kind));
ok("the nearest word wins", kindBefore("baptised on 3 May and died ") === "death");
ok("no word, no mark; a word in an earlier clause does not count", kindBefore("the entry of ") === "" && kindBefore("she died. The entry of ") === "");
ok("a range of years is one date, not two", factsOf("<p>the baptism book 1764–1791 and a marriage in 1800</p>").dates.map((d) => d.text).join("|") === "1764–1791|1800");
const g = factsOf("<p>She was born in 1828, and died in January 1800; the book of 1803.</p>");
ok("dates carry what they are the date of", g.dates.find((d) => d.text === "1828").kind === "birth" && g.dates.find((d) => d.text === "January 1800").kind === "death" && g.dates.find((d) => d.text === "1803").kind === "");
ok("no links, no names: nothing is invented", factsOf("<p>a sentence with no links</p>").people.length === 0 && factsOf("").sources.length === 0);

/* a register book named in the prose is linked to the volume the archive's catalogue holds, and only then */
const idx = bookIndex([
  { parish: "Svetvinčenat", label: "Births (Rođeni) 1709-1764", href: "https://fs/3:1:A" },
  { parish: "Svetvinčenat", label: "Births (Rođeni) 1764-1791, 1815-1874", href: "https://fs/3:1:B" },
  { parish: "Svetvinčenat", label: "Deaths (Umrli) 1791-1887", href: "https://fs/3:1:C" },
  { parish: "Svetvinčenat", label: "Marriages (Vjenčani) 1762-1858, 1855-1895", href: "https://fs/3:1:D" },
  { parish: "Pula", label: "Births (Rođeni) 1800-1850", href: "https://fs/3:1:E" },
]);
ok("a book kind is read from a volume label", bookKind("Births (Rođeni) 1584-1608") === "birth" && bookKind("Deaths (Umrli) 1791-1887") === "death" && bookKind("Marriages (Vjenčani) 1762-1858") === "marriage" && bookKind("Hearth tax 1700") === "");
ok("a volume's years are every range in its label", JSON.stringify(bookYears("Births (Rođeni) 1764-1791, 1815-1874")) === "[[1764,1791],[1815,1874]]");
const lb = (t) => linkBooks("<p>" + t + "</p>", idx);
ok("the Svetvinčenat baptism book 1764–1791 links to its volume", lb("The Svetvinčenat baptism book 1764–1791, read").includes('<a class="lk-book" href="https://fs/3:1:B"') && lb("The Svetvinčenat baptism book 1764–1791, read").includes(">Svetvinčenat baptism book 1764–1791</a>"));
ok("a year inside a volume's range links", lb("the Svetvinčenat baptism book 1770").includes("3:1:B"));
ok("a second range of the same volume links", lb("the Svetvinčenat baptism register 1815–1874").includes("3:1:B"));
ok("a burial book is a Deaths volume", lb("the Svetvinčenat burial book 1800").includes("3:1:C") && lb("the Svetvinčenat death book 1791–1887").includes("3:1:C"));
ok("a marriage book is a Marriages volume", lb("the Svetvinčenat marriage book 1800").includes("3:1:D"));
ok("years the volume does not hold are not linked", !lb("the Svetvinčenat baptism book 1792–1800").includes("lk-book") && !lb("the Svetvinčenat baptism book 1700").includes("lk-book"));
ok("a range spanning two volumes is not linked (no guessing)", !lb("the Svetvinčenat baptism book 1760–1770").includes("lk-book"));
ok("another parish's book is not linked to this one", lb("the Pula baptism book 1810").includes("3:1:E") && !lb("the Zagreb baptism book 1810").includes("lk-book"));
ok("the parish written without its diacritic still matches", lb("the Svetvincenat baptism book 1764–1791").includes("3:1:B"));
ok("text already in a link or code is left alone", !linkBooks('<a href="/x/">the Svetvinčenat baptism book 1764–1791</a>', idx).includes("lk-book") && !linkBooks("<code>Svetvinčenat baptism book 1764–1791</code>", idx).includes("lk-book"));
ok("no catalogue, no change", linkBooks("<p>the Svetvinčenat baptism book 1764–1791</p>", bookIndex([])) === "<p>the Svetvinčenat baptism book 1764–1791</p>");
ok("a linked book is a Source chip on the entry", factsOf(lb("the Svetvinčenat baptism book 1764–1791")).sources.length === 1);

/* a place named in the prose is linked to its page, with the flag that flew over it in the sentence's year */
const table = { Crikvenica: { today: { svg: "croatia-flags--era-1990.svg", label: "Croatia" }, eras: [[1867, 1918, "austria-flags--era-1867.svg", "Austria–Hungary"], [1951, 1986, "croatia-flags--era-1946.svg", "Yugoslavia"]] }, "Gračišće": { today: { svg: "croatia-flags--era-1990.svg", label: "Croatia" }, eras: [] } };
const pidx = placeIndex([{ name: "Crikvenica", href: "/places/crikvenica/" }, { name: "Gračišće", aliases: ["Galignano"], href: "/places/gracisce/" }, { name: "Rab", href: "/places/rab/" }, { name: "Po", href: "/places/po/" }], table, (f) => "/flags/" + f);
const lp = (t, seen) => linkPlaces("<p>" + t + "</p>", pidx, seen ? { seen } : {});
ok("a place links to its page", lp("born at Crikvenica").includes('<a class="lk-place" href="/places/crikvenica/"'));
ok("a year in the sentence picks that year's flag, and today's where another country's", (() => { const h = lp("He was baptised at Crikvenica in 1894."); return h.includes("austria-flags--era-1867.svg") && h.includes("croatia-flags--era-1990.svg") && h.includes("Austria–Hungary then; Croatia today"); })());
ok("an era flag of today's country shows once", (() => { const t2 = { X: { today: { svg: "croatia-flags--era-1990.svg", label: "Croatia" }, eras: [[1991, 2030, "croatia-flags--era-1990.svg", "Croatia"]] } }; const i = placeIndex([{ name: "Xyz", href: "/places/x/", flagKey: "X" }], t2, (f) => f); return (linkPlaces("<p>Xyz in 2000.</p>", i).match(/<img/g) || []).length === 1; })());
ok("no year in the sentence: today's flag only", (() => { const h = lp("born at Crikvenica"); return h.includes("croatia-flags--era-1990.svg") && !h.includes("austria-flags"); })());
ok("two different years in the sentence: no era is claimed", !lp("Crikvenica in 1894 and again in 1905.").includes("austria-flags"));
ok("the same year twice is one year", lp("Crikvenica in 1894, married 1894.").includes("austria-flags--era-1867.svg"));
ok("a work date (2020 or later) is not the event's year", lp("Crikvenica; read on 16 November 2026 (born in 1894).") !== "" && lp("Crikvenica in 1894 (checked 2026).").includes("austria-flags"));
ok("a year in another sentence is not this one's", !lp("Born at Crikvenica. He died in 1894.").includes("austria-flags"));
ok("a year with no era flag in the table: link, today's flag only", (() => { const h = lp("Crikvenica in 1840."); return h.includes("lk-place") && !h.includes("austria-flags") && h.includes("croatia-flags"); })());
ok("an old spelling links to the page of the place", lp("born at Galignano").includes('href="/places/gracisce/"'));
ok("only the first mention in an entry is linked", (() => { const seen = new Set(); const h = lp("Crikvenica and again Crikvenica", seen); return (h.match(/<a /g) || []).length === 1; })());
ok("a place already linked is left alone, and so is code", !linkPlaces('<a href="/x/">Crikvenica</a>', pidx).includes("lk-place") && !linkPlaces("<code>Crikvenica</code>", pidx).includes("lk-place"));
ok("a place is written with a capital, and a short name is not read", !lp("a boat to rab").includes("lk-place") && !lp("the Po valley").includes("lk-place") && lp("on Rab").includes("/places/rab/"));
ok("a place inside a longer word is not linked", !lp("Crikvenicanski").includes("lk-place"));
ok("a place with no flag in the table is linked and has no flag", (() => { const h = lp("on Rab"); return h.includes("lk-place") && !h.includes("<img"); })());
ok("no index, no change", linkPlaces("<p>Crikvenica</p>", placeIndex([], {}, null)) === "<p>Crikvenica</p>");
ok("yearAround reads one year only", yearAround("Born at X in 1894.", 8, 1) === 1894 && yearAround("X 1894 and 1900", 0, 1) === 0);
ok("a linked place is a Place chip with its flags", (() => { const f = factsOf(lp("Crikvenica in 1894")); return f.places.length === 1 && f.places[0].flags.length === 2 && f.places[0].name === "Crikvenica"; })());

/* a person's name is linked to the person, or, where several bear it, to the list of them */
const nidx = nameIndex({ people: [{ name: "Anna Bakar", aliases: ["Bakar Anna"], url: "/people/anna-bakar/" }, { name: "Maria Rossi", url: "/people/maria-rossi/" }], ambiguous: [{ name: "Giovanni Defranceschi", url: "/people/?q=Giovanni%20Defranceschi" }] }, { avoid: ["Maria Rossi Bianchi"] });
const ln = (t, seen) => linkNames("<p>" + t + "</p>", nidx, seen ? { seen } : {});
ok("a name borne by one person links to that person", ln("Anna Bakar was baptised").includes('<a class="lk-name" href="/people/anna-bakar/" data-autolink="person">Anna Bakar</a>'));
ok("a name several people bear links to the list, marked shared", (() => { const h = ln("Giovanni Defranceschi died"); return h.includes("lk-shared") && h.includes("/people/?q=Giovanni%20Defranceschi") && h.includes("Several people share this name"); })());
ok("an alias links to the same person", ln("Bakar Anna").includes("/people/anna-bakar/"));
ok("a person is linked once per entry across fields", (() => { const seen = new Set(); return (ln("Anna Bakar", seen) + ln("Anna Bakar again", seen)).match(/<a /g).length === 1; })());
ok("a name that overlaps a living or held-out name is not linked", !ln("Maria Rossi Bianchi was here").includes("lk-name"));
ok("a lone first name is not a name", !ln("Anna was here").includes("lk-name"));
ok("a name inside a link, a heading or code is left alone", !linkNames('<a href="/x/">Anna Bakar</a>', nidx).includes("lk-name") && !linkNames("<h3>Anna Bakar</h3>", nidx).includes("lk-name"));
ok("a name inside a longer word is not linked", !ln("Anna Bakarovic").includes("lk-name"));
ok("a shared name linked in the prose is a shared chip", (() => { const f = factsOf(ln("Giovanni Defranceschi")); return f.people.length === 1 && f.people[0].shared === true; })());

/* "dead" before a date is a death ("born 1934, dead October 1955"); "dead" anywhere else is not */
ok("'dead' straight before a date is a death", kindBefore("born 1934, dead ") === "death" && kindBefore("dead in ") === "death" && kindBefore("dead on ") === "death");
ok("'dead' elsewhere is no mark", kindBefore("the dead man's letter of ") === "" && kindBefore("he was left for dead; the entry of ") === "");
ok("a quoted index entry gets a birth and a death mark", (() => { const f = factsOf("<p>index entry 'born 1934, dead October 1955'</p>"); return f.dates.find((d) => d.text === "1934").kind === "birth" && f.dates.find((d) => d.text === "October 1955").kind === "death"; })());

/* the ledger view: a colour only for a real severity, a card from the archive's own sentences, a heartbeat of the days */
ok("severity words get their tone, any case", toneOf("Serious") === "serious" && toneOf("MAJOR") === "major" && toneOf("moderate") === "moderate" && toneOf("Minor") === "minor");
ok("a status is not a severity: resolved, documented, Process, Not ours are 'other'", ["resolved", "documented", "Process", "Not ours", "candidate", "addition", ""].every((v) => toneOf(v) === "other") && toneOf(undefined) === "other");
ok("the archive's own gravest word is at least 'serious'", toneOf("withdrawn", "withdrawn") === "serious" && toneOf("withdrawn") === "other");
ok("every tone is one the page draws", ["major", "serious", "moderate", "minor", "other"].every((t) => TONE_ORDER.includes(t)));
const card = cardOf({ was: "<p>That CEMLA lived at <a href=\"/x/\">cemla.org</a></p>", now: "<strong><em>THE ARK WAS THE WRONG ONE, and both rows carried it.</em></strong> That ark is the confirmation." });
ok("the title is the claim that was retracted, without markup", card.title === "That CEMLA lived at cemla.org", card.title);
ok("the verdict is the loud opening of the answer", card.verdict === "THE ARK WAS THE WRONG ONE, and both rows carried it.", card.verdict);
ok("no loud opening: the first sentence of the answer", cardOf({ was: "That a thing", now: "<p>It is a different thing. More follows here.</p>" }).verdict === "It is a different thing.");
ok("an archive that keeps the headline in kind: that is the title", cardOf({ kind: "A reading of the plate that the whole index had copied without checking", was: "x y z", now: "It said so." }).title.startsWith("A reading of the plate"));
ok("a short category in kind is not the title", cardOf({ kind: "Birth year", was: "That he was born 1833", now: "Born 1836." }).title === "That he was born 1833");
ok("no claim: the answer's first sentence is the title and the verdict is not repeated", (() => { const c = cardOf({ now: "She was born in Cordoba. Later notes follow." }); return c.title === "She was born in Cordoba." && c.verdict === ""; })());
ok("a long title is cut at a word", cardOf({ was: "word ".repeat(80), now: "x" }).title.length <= 160 && cardOf({ was: "word ".repeat(80), now: "x" }).title.endsWith("…"));
ok("a row with nothing yields empty strings, not an error", (() => { const c = cardOf({}); return c.title === "" && c.verdict === ""; })());
const hb = heartbeat([{ when: "8 Nov 2026", sev: "serious" }, { when: "8 Nov 2026", sev: "minor" }, { when: "10 Nov 2026", sev: "resolved" }, { when: "Sept 2026" }, { when: "" }]);
ok("a heartbeat runs first to last day, one bar a day, gaps included", hb && hb.bars.length === 3 && hb.from === "2026-11-08" && hb.to === "2026-11-10" && hb.bars[1].n === 0, JSON.stringify(hb));
ok("each bar counts by tone; a month alone is no day", hb && hb.bars[0].tones.serious === 1 && hb.bars[0].tones.minor === 1 && hb.bars[2].tones.other === 1 && hb.bars.reduce((a, b) => a + b.n, 0) === 3);
ok("fewer than two dated days: no heartbeat", heartbeat([{ when: "8 Nov 2026" }, { when: "8 Nov 2026" }]) === null && heartbeat([{ when: "1814" }, { when: "" }]) === null && heartbeat([]) === null);
ok("a long span is bucketed, not drawn as hundreds of bars", (() => { const h = heartbeat([{ when: "2025-01-01" }, { when: "2026-11-01" }], undefined, "major", undefined, 120); return h.bars.length <= 120 && h.size > 1 && h.bars.reduce((a, b) => a + b.n, 0) === 2; })());
ok("entities come back as characters in a title", cardOf({ was: "<p>That Aguilar&#39;s row said &quot;andaluz&quot; &amp; more&#x27;</p>", now: "x" }).title === "That Aguilar's row said \"andaluz\" & more'");
ok("a date reads out in words", longDate("2026-11-08") === "8 November 2026" && longDate("") === "");
ok("a kind filter only where kind is a short category", kindFilterable([{ kind: "Birth year" }, { kind: "Birth date" }, { kind: "Birth year" }]) && !kindFilterable([{ kind: "x".repeat(80) }, { kind: "y".repeat(90) }]) && !kindFilterable([{}, {}]) && !kindFilterable([{ kind: "Same" }, { kind: "Same" }]));
if (bad) { console.log(bad + " failed"); process.exit(1); } console.log("all passed");
