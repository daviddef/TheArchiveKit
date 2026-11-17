// node kit/tools/corrections_logic.mjs : what the Corrections page and /whats-new/ must agree on (lib/corrections.js): one stable anchor per correction
// row, the same on both sides, and the page's newest-first order. Cases are written from the shapes the archives keep corrections in.
import { corrIdMap, byDateDesc, factsOf, kindBefore } from "../lib/corrections.js";
import { bookIndex, linkBooks, bookKind, bookYears } from "../lib/booklinks.js";
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
if (bad) { console.log(bad + " failed"); process.exit(1); } console.log("all passed");
