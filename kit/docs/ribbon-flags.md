# Mini flags on the ribbon cards

Written 27 October 2026. David asked for the flags of the Record Atlas / Flags Atlas as mini flags on each generation card, "showing
where". This is the design, the rule that picks a flag, and the gate. It is the "at the time" note (`docs/era-notes.md`) drawn as
a picture, so it keeps that note's rules, and adds one of its own: a picture is believed faster than words, so where the note would
hedge ("From that year: ..."), the flag says nothing.

## What a reader sees (third version, 27 October 2026)

- **A strip in the card's header row.** Each card's flags sit together at the ends of the row that holds the glyph and "Gen. n":
  two stacked at the right end, a third and fourth at the left end (a family card: one row at the right end, its "Gen. n" moved to
  the row's left end). Absolutely placed: the card is exactly the size it is without them, and they touch no word
  (`checkflagfit.mjs`). 12px high, 3:2, a hairline edge, 2px corners, the same on a phone.
- **What is in it.** For each place the card names, in the order from, at, spouse: the **era flag** (the state that held the place in
  the card's year) and **today's flag** (the country the place is in now) where it is another country's flag (Canelones 1791: Spain,
  then Uruguay); where the era flag is today's country's (Italy, Spain, Argentina, the United Kingdom: one Flags Atlas page) only the
  era flag; where the era cannot be said (no assessed era, contested, a boundary year, a regime with no flag, a flag left out)
  today's alone. A flag two places share is drawn once. At most 4 marks: past that, 3 flags and a "+n" whose words list the rest
  (a family card: 3 marks).
- **Which place.** Each flag's alt (accessible name) and title (tooltip) name the place it is for: `at Canelones, 1791: Spanish
  Empire then`, `at Canelones: Uruguay today`, `from Córdoba: Spain today`; a shared flag lists each place (`from Senj: Croatia
  today; at Senj: Croatia today`). A reconstructed flag adds "(reconstructed)", an emblem "(an emblem)". A living card (a minor, a
  living spouse's line) has today's flag only, never a year.
- **Evidence.** A flag that stands for the from line carries the card's evidence ring: dashed on an inferred card, dotted on family
  memory. Today's flag has a dotted lower edge.
- **Key and credit**, one short line under the ribbon: *Flags at a card's top: each place's state then, and today's where it
  differs (hover for which place).* *Flags: Flags Atlas, by David Defranceski, drawn for this project.* (`data-flag-credit="1"`).
- Where nothing can be said, **nothing**: no grey box, no words.

## Today's country (the coverage rule)

Today's flag needs only the place's country now, so every place line whose country can be named gets at least that. The country
comes from, in order: **the card's own words** (a comma part that is a country or its alias: "Benevento, Italy", "Estado Oriental
del Uruguay"); **the archive's own** (an optional `--countries` file `{card text: ISO code | null}`, then its era snapshot: the
region the place is filed under, where that region lies in one country today); **the kit's table** `data/place-countries.json`
(226 places and regions: Montevideo, Canelones -> Uruguay; Cape Town, Wynberg, Brakpan, Germiston -> South Africa; Senj, Selce,
Karlobag -> Croatia; Devon -> the United Kingdom; Carnia -> Italy ...). A name two countries have (Córdoba: Spain and Argentina;
Rosario: Argentina and Uruguay; the River Plate; Istria and Dalmatia, split today) is in the table's `ambiguous` list and is never
read from it: only the card's words or the archive's own table can place it. Two sources that disagree give nothing. The flag is the
present flag of that country's Flags Atlas page (`index.json` `today`). An archive that knows its "Córdoba" is Spain's says so in
its `--countries` file, one line; the kit does not guess.

## Left out, deliberately

The flags of hate-symbol and occupation regimes are **left out entirely** (David, 27 October 2026): Nazi Germany, the NDH, the RSI,
the Arrow Cross, the National Legionary State, Vichy, Nedić's Serbia, the German occupations of Norway and the Netherlands, the German
and Soviet occupation of Poland, Allied-occupied Germany, Italian-occupied Albania and Montenegro (`withheld` in
`data/regime-flags.json`; the gate fails a table that names one, and their art is not in the kit). For those years no era flag is
drawn, and the card falls back to today's country flag alone. This is a decision, not a gap.

## How a flag is chosen (the chain)

1. **The place**, as the card prints it: `origin`, `atPlace`, `spouseOrigin` (its leading "of " taken off). An archive whose card
   prints a place another way than its era table does may give `--alias` (`{card text: the era table's text | null}`).
2. **The year** of the line: `at` = `atYear`; `from` = the card's `originYear` if it states one, else the first plain year of `years`
   ("1882–1950" -> 1882, "named 1791" -> 1791; "c.1767–...", "by 1882" have none), else `atYear`; `spouse` = `spouseOriginYear` if
   stated, else the from line's year. A year that is not four plain digits gives no flag. A living line uses this year, and draws no year.
3. **The region era** (for the era flag; today's flag comes from the country rule above), from the archive's committed **era snapshot** with the kit's era library (`eralib.era_at`): the same table, rings,
   edge agreement, margins, quiet rule and refusals as the era notes. Then the flag adds its own refusals: a **boundary year**
   (the note says "From that year"; a flag cannot hedge), an **unassessed** era (even where the archive allows them for notes), a
   **contested** era (whatever its scope). A living line asks for the era running now (`to` null) and ignores the quiet rule.
4. **The regime -> the flag**: `kit/data/regime-flags.json`, reviewed by hand against each flag's own `polity` in contract 1.13.0. It
   lists, per regime, the Flags Atlas flag eras that stand for it, and per region era (`eras`) a list that REPLACES the regime's. The
   Atlas's own `regimes.archives` ("whose flag was over the parish") is the starting point and is overruled where it leads to another
   polity's flag: the Italy page's flags of 1814-1861 are Sardinia's, so Naples and the Two Sicilies get none; "Habsburg" covers the
   Austrian and the Hungarian crowns, so only Austrian crown lands get the Austrian Empire's flag (from 1804) and Cisleithania's
   (1867-1918); "Napoleonic" covers several states, so only the French Empire's own ground gets France's; the Union of South Africa
   (filed under "Britain") gets its own flags. An empty list is a decision: no flag.
5. **The year picks one flag** of that list: the flag era whose `from <= year < to` (open: `present`). None, or more than one: silence.
   It must be of an evidence class the table allows (`attested`, `reconstructed`, `symbolic`; never `unconfirmed`, `unreviewed`,
   `placeholder`, `none`), must have art in the Atlas, and must not be **left out** (above).
6. **An edge place** (the snapshot holds it to its neighbours) gets a flag only if every neighbouring region's era gives the same flag.

The silences are counted by reason (`no-region`, `edge`, `era-refused`, `margin`, `year`, `no-flag`, `boundary`, `unassessed`,
`contested`, `flags-overlap`, `evidence`, `no-art`, `edge-flag`, `same-as-from`, ...).

## Files

| File | What it is |
|---|---|
| `components/FlagMini.astro` | one flag on one line; resolves the kit's svg through the build (`import.meta.glob`), so an archive copies nothing |
| `lib/flags.js` | what may be drawn (`flagsOn`), the strip (`stripOf`, `slotClass`, `FLAG_CAP`), `FLAG_CREDIT`, `FLAG_KEY` |
| `components/StoryRibbon.astro`, `components/FamilyRibbon.astro` | draw `card.flags` and the key-and-credit line; no `flags`, no change |
| `styles/story.css` | `.flag-strip`, `-left`, `-3`, `.flag-mini`, `-inf`, `-lore`, `-today`, `.flag-more` (both ribbons load it) |
| `data/place-countries.json` | today's country of a place: countries (name, Flags Atlas page, aliases), 226 places, the ambiguous names |
| `data/regime-flags.json` | the table (step 4) |
| `data/flags/*.svg`, `data/flags/index.json` | the 111 Flags Atlas flags the table can draw for some year of some region era, each with its years, polity, evidence and sha256; 3 named flags with no art listed for their years only; `unpicked` names the table's flags no region era can reach |
| `tools/ribbonflags.py` | the generator: `--write` / `--check` the cards' `flags`; `--sync-atlas` refreshes `data/flags` from the Atlas |
| `tools/checkribbonflags.py` | the data gate, with `--selftest` (a planted fault for each rule) |
| `tools/checkflagfit.mjs` | the box gate: no card taller or wider with its flags (a browser; `--selftest`) |
| `tools/ribbonflags_logic.mjs` | `lib/flags.js`'s refusals and the kit's flag files |

A card's flag: `{kind: era|today, line: from|at|spouse, place, svg, flag, era, year (null for today's), label, grade, assessed}`.
`grade` is the card's `originGrade` (the card's outline); `assessed` is true for every era flag (an unassessed era gives none) and
says, for today's flag, whether the era running now is assessed (today's flag follows the snapshot's own unassessed policy).

## Using it in an archive

```
python3 node_modules/@daviddef/archive-kit/kit/tools/ribbonflags.py --snapshot src/data/era-snapshot.json \
   --story src/data/story.json --family-lines src/data/family-lines.json [--alias src/data/flag-places.json] \
   [--countries src/data/flag-countries.json] --write
python3 node_modules/@daviddef/archive-kit/kit/tools/checkribbonflags.py --snapshot src/data/era-snapshot.json \
   --story src/data/story.json --family-lines src/data/family-lines.json --dist dist
```

Run the generator after the snapshot or the cards change, and commit the result with them; the gate in the build fails a stale card
(R7), so the flags cannot drift from the era rules. A family-lines file that is REBUILT by the archive's own tool (Lerena's
`build-family-lines.py`) must keep `flags` or run the generator after it. Family ribbons drawn from a `lane` have no stored cards
and get no flags (listed). Markup tools that match the ribbon's markup should allow `span.flag-strip` with `data-flag-strip`, `img.flag-mini` with
`data-flag*`, `span.flag-more`, and `p.st-rb-fl` / `p.fr-fl` with `data-flag-credit`.

## The gates

`checkribbonflags.py` (the data, recomputed independently; `--selftest` plants 25 faults beside two clean runs): R1 the file is the kit's and listed
(sha256), every svg listed; R2 a label; R3 a known kind and line, one of each kind per line, on the line that names its place; R4 no
flag where the rules are silent; R5 no era flag on a living line and no year on today's; R6 equal to the recompute (file, flag, era or
country, year, label, grade, assessed); R7 no flag missing; R8 the table names only flags the index accounts for, none left out, evidence
allowed; R9 built: alt = title, not empty, a line, inside a ribbon card, the credit on the page; R10 never today's flag beside an era
flag of the same country.

`checkflagfit.mjs` (the boxes, in Chrome through playwright-core, which is not a kit dependency, so it is not in `npm test`):
`node checkflagfit.mjs --url <built page> ... [--widths 1440,1100,390]` measures every ribbon card with its flags and with them
hidden; any card whose height or width changes by more than 0px fails, and so does a strip that touches the glyph, "Gen. n", the
name or the years. `--selftest` passes a fixture ribbon and catches three planted faults (the strip in the flow; the strip moved
onto the name; flags 30px high in the flow).

## Licence and provenance

The flag artwork is David Defranceski's own project's (the Flags Atlas, in the Record Atlas at `site/public/fl/`), drawn for him, with
no declared licence. He asked for it on his own archive sites (27 October 2026). The kit carries only the flags the table can draw,
says whose they are wherever they are shown, and **claims no open licence** for them (`index.json` `licence`).

## Counts (27 October 2026, third version, the archives' committed snapshots)

| Ribbon | place lines | with a flag (era / era+today / today) | none, and why | flags shown |
|---|---|---|---|---|
| Lerena story | 17 | 12 (1 / 2 / 9) | Córdoba x2 and the River Plate (two countries possible), Córdova la Llana (not in any table), "place not known" | 11 |
| Falco story | 21 | 20 (9 / 0 / 11) | "place not known" | 12 |
| Blažević story | 18 | 17 (0 / 0 / 17) | "place not known" | 10 |
| Blažević, Papić family | 7 | 7 (0 / 0 / 7) | none | 3 |

"Flags shown" counts each card's distinct flags (a flag two places share is drawn once). At 1440, 1100 and 390, light and dark,
every card of the four ribbons is the same height and width with and without its flags, and no strip touches a word
(checkflagfit: max delta 0px).
