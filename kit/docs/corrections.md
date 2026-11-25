# The corrections page, and how /whats-new/ points at it

`components/Corrections.astro` draws the page; `lib/corrections.js` is what it and `/whats-new/` (`lib/pulse.js`) must agree on.
Changed 17 Nov 2026 after David's five questions on the Defranceski page; it applies to all eight archives.

| David asked | what the kit does now |
|---|---|
| why are they not sorted by date, newest first? | The component sorts by `when` itself (`sort="date"`, the default). A date it cannot read goes after the dated rows; rows on one day keep the archive's own order (so an archive may still put the serious ones first within a day). `sort="given"` keeps the archive's own order. Do NOT pre-sort the rows by severity in the archive's page: that was the cause. |
| the What's new card goes to the page, not to the correction | Each correction has an anchor, `c-<day>-<hash of the headline>` (`corrIdMap(rows)` in `lib/corrections.js`). `buildPulse` links the card to `/corrections/#<anchor>`; the page puts the same anchor on the entry (`id:` in each row) and highlights it. If a filter is hiding the entry, the page clears the filters first. The page reads the address BEFORE it draws, because drawing rewrites it; the entry a wide screen opens by itself is not written into the address, only one the reader or a link chose. After any change to the component's script, open `/corrections/#<an older entry>` on a wide and a narrow screen: the build cannot see this. |
| people in an entry are plain text | Two causes. The archive's page must let the build's name linker in (some archives mark `<main>` `data-no-autolink` except on chosen pages), and the card is marked `data-no-autolink` so that the link lands in the full entry, not the card. A name two people bear links to the roster search; a name with no page stays plain. |
| the date of a long day gets lost | One heading per day (a day is now ONE group, because the rows are sorted), and the heading stays at the top while its entries scroll under it. The component measures a sticky or fixed site header (`header.site`, or a `header` directly in `body`) and stops below it; a page with some other header sets `--cx-top` to its height, and that value wins. |
| who is this about? | A row can carry `for: [["/people/slug/", "Name"], ...]` (the same list a search row uses: the archive's own pages for the people, never a person it does not publish). The page shows "About Name" on the entry (map it to `about:`), and the What's new card shows it under the headline. The kit does not guess a name: a row with no `for` names nobody, and the card says nothing. |

| long paragraphs; people with no link; where are the sources? (18 Nov) | Each entry opens with a strip of **People, Places, Sources, Dates** read out of the sentences the archive already wrote: a person or place is the link the archive already made (`/person/`, `/places/`), a source is a record link (`lk-rec`) or any address off the site, a date is a date in the text (the work date, 2020 or later, is left out); a date wears a mark from the word just before it: † died or buried, ✶ born or baptised, ⚭ married (a heuristic: the word must lead straight to the date, and the years of a book or a range such as 1764–1791 get no mark, so a few events go unmarked rather than wrongly marked). Chips are links where there is a page. Nothing is invented: if the text names a FamilySearch image without linking it, there is no Source chip, and the fix is the archive writing the record link into the correction (`[words](rec:fs-<ark>)` or a URL). `facts={false}` turns the strip off. |

| a book named in the prose ("The Svetvinčenat baptism book 1764–1791") is not a link | `lib/booklinks.js`: `bookIndex(rows)` takes the archive's own catalogue of register books (`{parish, label, href}`), and `linkBooks(html, index)` (the Corrections `books` prop) links a phrase "<parish> <baptism / burial / death / marriage> book <years>" to its volume, **only** when the catalogue answers it: same parish, same kind (baptism = a Births volume, burial or death = Deaths, marriage = Marriages), years inside the volume's years. No match, or two different volumes, leaves the words as written. A linked book also becomes a Source chip. |
| "the husband of 1762–64": why not name him? | The strip also reads the entry's footer ("Corrected in place: the roster notes of …"), so the people the correction touches are named and linked even when the sentence says only "the husband". Putting the name in the sentence itself is the archive's wording. |

| places named in the prose (Crikvenica) have no link and no flag | `lib/placelinks.js`: `placeIndex(rows, flags, flagUrl)` takes the archive's places that have a page (`{name, aliases, href}`; aliases are the old spellings, so Galignano goes to Gračišće) and the flag table `kit/tools/placeflags.py` writes from the archive's era snapshot and the kit's regime table. `linkPlaces` links the FIRST mention in an entry and draws the flag of the state that held the place in the year the sentence names, plus today's where it is another country's. One year in the sentence or none: two different years claim nothing, and a year of 2020 or later (the day the correction was made) is not read. Where the era table is silent, the link has today's flag only; no page, no link. The Places chip carries the same flags. |
| a name shared by several people is not linked | `lib/namelinks.js`: `nameIndex(idx)` reads the SAME index the archive builds for `tools/autolink.py` (`people`, `ambiguous`), so no second list. A name of one person links to them; a name several bear links to the archive's list of them (class `lk-shared`, "Several people share this name"), never to one of them. Names that overlap a living or held-out name (`avoid`) are not linked. The People chip shows `⋯` for a shared name. |

## What an archive does (about ten lines in its own `corrections` page)

```astro
import { corrIdMap } from "@daviddef/archive-kit/lib/corrections.js";
const ids = corrIdMap(c.rows);              // c.rows in FILE order, the same list the build passes to buildPulse as `corrections`
...
<Corrections rows={c.rows.map((r) => ({ ..., id: ids.get(r), about: r.for }))} />   // no sort of its own
```

The `ids` must come from the SAME rows `buildPulse` gets (`corrections: c`), in file order; otherwise the anchors do not match and the card falls back to the top of the page.
Putting a `for` on each correction row is the archive's work, from its own data: who the correction is about, one page per person, the archive's own pages only.
Defranceski's catalogue is `parishbooks.json`: `bookIndex(pb.list.flatMap((p) => p.books.map((b) => ({ parish: p.parish, label: b, href: ark(p.parish, b) }))))`, with `href` the volume's FamilySearch image (`https://www.familysearch.org/ark:/61903/` + the `ark` in `pb.links`), passed as `books={…}`; a volume with no `href` is left out.
`node kit/tools/corrections_logic.mjs` holds the anchors, the order and the card links to cases.

### Places and shared names (opt in with two props)

```astro
import { placeIndex } from "@daviddef/archive-kit/lib/placelinks.js";
import { nameIndex } from "@daviddef/archive-kit/lib/namelinks.js";
const places = placeIndex(placeRows, placeFlags, (svg) => flagUrlFor(svg));   // placeRows: [{name, aliases, href}] of the places with a page
const names = nameIndex(autolinkIndex, { avoid: livingNames });                 // the file autolink.py already reads
<Corrections places={places} names={names} books={books} rows={...} />
```

`placeFlags` is `python3 kit/tools/placeflags.py --snapshot era-snapshot.json --places place-rows.json --alias flag-places.json --countries flag-countries.json --out place-flags.json`, run in the archive's build; `flagUrlFor` maps a flag file name to the address the archive serves it at (the kit's art is in `kit/data/flags/`). Without the props nothing changes. The era flag is only as wide as the era snapshot: a place the snapshot does not assess in that year gets today's flag only, never a guess.

**Serve the flags as files, not data URIs.** Vite inlines a small SVG as a `data:` URI once per use, so a page with hundreds of place links grows by hundreds of KB (Falco 1.6 -> 2.1 MB, D'Arcy 174 -> 250 KB, Blazevic +77 KB). Build `flagUrl` from `import.meta.glob("<path to kit/data/flags>/*.svg", { eager: true, query: "?no-inline", import: "default" })`: the flags are emitted once as `/_astro/<name>.svg` and every link points at the file (Falco 2.1 -> 1.59 MB, D'Arcy 250 -> 190 KB, Blazevic +12 KB). Check the built page has no `data:image/svg` in it.

## The ledger view (26 November 2026): cards, a reading pane, a heartbeat, search

David, on the Lerena page: "really ugly, width's still not right, overwhelming amount of text, not fun, needs better integration, linking, colour, searchability". The page was one long stack of full paragraphs (Lerena 87,000 px; Falco 427 entries, 157,000 words) in a 70-character column that left the right half of a wide screen empty. Nothing about what an archive passes in changed; the component draws it differently.

| what | how |
|---|---|
| a card per correction | title = the claim retracted (`was`), or the headline in `kind` where an archive keeps one there (Falco, Defranceschi, Blažević); verdict = the loud opening of `now`, else its first sentence; then the grade, the short kind, and who it is about. `cardOf` in `lib/corrections.js`; every word is the archive's own, none is written by the kit |
| the reading pane | wide screens (1000px and up): the open entry beside the list, sticky, with Newer / Older and "Copy a link". Narrow: the entry opens under its card. Without script: every entry stays open as before |
| was beside now | two boxes ("What was published", "What is true"), how it was caught under them (the `moreLabel` prop names that box: "How and why" by default), then the People / Places / Sources / Dates strip |
| the heartbeat | one bar a day first to last (a bar is a week or more where the span passes 120 days), stacked by grade; a click reads only those days. Not drawn when fewer than two exact days are dated (Mazza's rows carry no day). `heartbeat` |
| colour | only major, serious, moderate and minor are colours (`toneOf`); every other grade word (Falco's resolved, new, finding; Mazza's documented, probable) is "other", so a status is never painted as a danger. The archive's own word is still the label |
| search and filters | one box over every word of every entry, accents folded; the grade (chips up to seven, else a select), the kind (only where it is a short category on 60% or more of the rows: `kindFilterable`; Falco's 415 headlines are not a filter), and "About anyone" from the rows' `about` list |
| the address | filters in the query (`?q=serena&sev=serious`, also `who` and `day`), the open entry in the hash (`#c-...`), so /whats-new/ links still land on their entry, and a view can be sent. If a link's entry is hidden by a filter, the filters clear first |
| removed | "Open every note" (the pane shows the whole entry) and the folded `<details>`. An archive's own contents list of days above the component (Lerena had one) is now redundant: the heartbeat is that list |

Not done here, and a good next step: place chips with flags in the filters, "Corrections about this person" on person and place pages, and the entry text out of the page into a file fetched on demand (Falco's page is 1.7 MB).
