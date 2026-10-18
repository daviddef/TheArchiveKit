# "At the time" notes: who held the ground, from the Record Atlas's context contract

Written 18 October 2026; second version the same day, rebuilt on the Atlas's versioned `context.json` (contract 1.7.0) in place of `regions.json`; third version the same day (snapshot version 3, contract 1.8.0 and later): the rings come from the contract, the style appears only on a page that has a note, a place near a ring edge keeps its note where the region across the edge has the same regime, and a note records whether the era it rests on was assessed. Pilot: the Mazza and Falco archives' person pages. Study behind it: the flags coverage study of the same day.

## What it is

Beside a dated place-event on a **deceased** person's page, a small muted line:

> Briatico · 1860 · *· At the time: Naples / the Two Sicilies* per the Record Atlas

It is **context about the ground, never a claim about the family**, it says where it came from, and where the data does not support it there is **nothing**: silence beats a wrong note. Text only: no flag image, no ruler, no language of administration, no "before/after" events, no live fetch.

| Piece | File |
|---|---|
| the rules, pure (no I/O) | `kit/lib/era.js` (`eraAt`, `whyNot`, `plainYear`, `fold`, `eraHref`, `renderEra`) and its Python twin `kit/tools/eralib.py` |
| the note, and its style (drawn once, on a page that has a note) | `kit/components/EraNote.astro`, `ERA_CSS` in `kit/lib/era.js` |
| the snapshot builder | `kit/tools/erasnap.py` |
| the gate on a built site | `kit/tools/checkera.py` |
| shared cases (both halves run them) | `kit/data/era-cases.json` (hand-written expectations) |
| tests with a planted fault per rule | `kit/tools/era_logic.mjs` (node), `kit/tools/era_selftest.py` (python) |

## The contract, and what this reads of it

`https://recordatlas.org/context.json` is documented at `/data/#context`. Each region era has a **permanent id** (`<region>--era-<from>`; the note's `data-era` is that id), `from`, `to` (`null` = still running, with `present: true`), `regimeLabel` (the display label), `polity`, `basis` (where the region's bands came from), `contested` and `approx`, and a `url` that lands on the era. The file also has a `rule` (how to look a year up), a `quality` block (gaps and overlaps, where a lookup must stay silent) and `countries` (the flag-page layer). Its `contract.version` is semantic: `erasnap.py` reads **major version 1** and refuses anything else, and records the version, the `generated` stamp and the sha256 of the file in the snapshot. From **1.8.0** each region also carries its `ring` and `bbox`, and the 16 regions written in October 2026 (more with each release) carry assessed `contested` and `approx` values, with a `why` where one is true.

**Read:** `regions` only. **Not read:** `countries`. That layer is keyed on flag pages, most eras are unreviewed, and a sub-national place needs the sub-national answer; the archive's own place-to-region table decides which region a place is in, and a place no region covers gets no note (the contract's advice to "fall back to countries" is deliberately not taken).

**The rings are in the contract (from 1.8.0)**: each region's `ring` (`[lat, lon]` vertices, approximate by design) and `bbox` (`[south, west, north, east]`). `erasnap.py --contract` reads them by default and records `atlas.rings_source = "contract"`; it stops if a bbox is not its ring's own extent (the contract would contradict itself), and refuses a contract older than 1.8.0 unless the rings are given. `--rings <file>` (the Atlas's `regions.json`) is an **optional override**: the snapshot then says `rings_source = "file"` with the file's sha256, the file must describe the same regions and eras as the contract, and only the file carries the `regimes.existed` dates behind the "era outside the dates the Atlas holds for its regime" refusal (nothing the contract holds today trips it). `--no-rings` says no place is edge-checked.

## The rules, and why each exists

- **a. Region eras only**, mapped from the place by the archive's table (above).
- **b. The interval is half-open: `from <= year < to`**, as the contract states it. A note needs a place that maps to a region and a year inside exactly one era with a whole-number `from`, a `to` that is a whole number or `null`, and a non-empty **display label**. The label is the contract's `regimeLabel`, never the era's free-text `polity` (which can carry today's province: "Italy - Provincia di Vibo Valentia" for a town that is in Reggio). Two exceptions, both in `erasnap.py`: a regime the Atlas itself calls shorthand rather than a state (`feudal` = "Aquileia · Gorizia · Frankopan", `german` = "German occupation", `--refuse-regimes`) is refused; a regime that is a bare shorthand (`napo` = "Napoleonic", `--qualify-regimes`) is shown with the era's own polity ("Napoleonic — Illyrian Provinces"; "Napoleonic Kingdom of Naples" already begins with the label), and refused where the era has no polity. Nothing is invented. An era outside the dates the ring file holds for its regime (`existed`) is refused.
- **c. Never on a living, held-out or noindex page.** The library cannot know who is living, so the *page* must not call it for them, and `checkera.py` fails the build on a note found on a noindex page, a `data-living` page, or a page in the archive's living list.
- **d. A year on a boundary.** The contract's rule says a year equal to a boundary belongs to the newer era, and `erasnap.py` records `policy.boundary = "newer"` only if the contract's `rule` text says so (otherwise `"silent"`, and a boundary year gets no note; `--boundary silent` makes it stricter, never looser). The contract's own documentation adds that "a consumer holding only a year should say «in that year» or stay silent", and a year-only date cannot say which side of the change the event fell. So a boundary-year note resolves to the newer era (the contract's rule) but is **worded so that it is true either way**: `· From that year: <the newer label> per the Record Atlas`, marked `data-era-boundary="1"`, and checked by the gate. A year is a boundary only where another era (kept or refused) of the same region ends in that year; the first year of a region's first era, or of an era after a gap, is an ordinary year. A date the page marks uncertain ("c. 1860", "before 1860", "1860?") has no year at all: `plainYear(date, year)` gives a year only for "1860", "March 1860", "12 March 1860" or ISO, and only if it agrees with the number the archive holds. (Not handled, said plainly: events before 1752 in England, or in the Julian calendar, where the year begins on a different day. An archive that has them must hand `null`.)
- **e. The link goes to the era**, the contract's own `url` on the Atlas's base (the contract asks for a citation with a link to the era's url), accepted only if it is the path the id implies. `data-era` is the contract's era id.
- **f. Circularity.** An era whose `basis` begins `seeded:` (today `seeded:defranceschi-sovereignty`: istria-central, istria-south, istria-west, kvarner, carnia, dalmatia) was taken from this estate's own research. The snapshot carries `seeded_from_archive` on it and the note says "per this archive's own research". `basis: "unknown"` (imotski: written in the same first batch, never checked) and `not-recorded` ("the file does not say") keep the standard words, and the basis is carried so an archive can count them.
- **g. null is not false; assessed is recorded.** The contract carries `contested` and `approx` as `null` on a region era when nobody has assessed it, `false` when someone looked and found it clean, and `true` (with a `why`) when it is a problem. An era is **assessed** when neither is null; the snapshot carries `assessed` and the contract's `why` on every kept era. `erasnap.py` **refuses** a null era by default (`--unassessed refuse`, reason "contested or approx not assessed (null)"), and refuses an era marked `true`. The library repeats the rule: an era whose flags are null is silent unless the snapshot's `policy.unassessed` is `"allow"`, and a flag that is neither true, false nor null is read as true. In contract 1.7.0 every one of the 347 region eras was null on both; from 1.8.0 some regions are assessed, so a build that refuses the unassessed keeps notes on those and no others. `--unassessed allow` is the deliberate, recorded choice to note the unassessed ones anyway: it is written into the snapshot's policy, and **each note says which kind it rests on** (`data-era-assessed="1"` on an assessed era, `"0"` on one the Atlas has not assessed; the library's `eraAt` returns `assessed` and `unassessed`). The gate prints, on every build, the counts of notes on assessed and on unassessed eras, fails a note whose mark disagrees with the snapshot, and `checkera.py --strict-unassessed` refuses the allow policy. The right fix is for the Atlas to assess eras; until it does, an archive that allows them is stating, in its own commit, that it accepts the Atlas's dates unassessed.
- **h. The quiet rule.** An event in the era that is still running (`to` null) in or after `recent_from` (default **1990**) gets no note: a modern event teaches nothing. Parameterised: `erasnap.py --recent-from N` writes it into the snapshot's policy and the gate holds the page to it; `eraAt(snap, place, year, { recentFrom: N })` overrides it for one call (`Infinity` switches it off); `eralib.era_at(..., recent_from=N)` the same in Python. It applies only to the running era: a closed era is not "modern".
- **i. Edge: quiet only when it matters.** The rings are 4-11 vertex shapes, "approximate by design", so a town near a ring edge may belong to the region across it. With the place's coordinates, `erasnap.py` finds a place that is within `--edge-km` (default **15**) of its own region's ring edge, inside or outside it (**near an edge**), or inside another region's ring and not its own (**in conflict**), and for it the **neighbours**: the other regions whose ring contains the place or lies within `--edge-km` of it. A place the archive's table marks `"edge": true` is silent (`marked-edge`). The distance is measured in a flat projection around the point (1 degree of latitude is 111.195 km, longitude scaled by cos latitude) to the ring's edges as straight lines between its `[lat, lon]` vertices.
  - **Where nothing across the edge can claim it, or the neighbours cannot be known**, the place is refused for every year, as before: no neighbour to compare (the place may be on ground no region covers), or some region of the contract has no usable ring. It is listed in `places_silent` ("edge", or "ring-conflict" for a place inside another's ring) so it can be counted.
  - **Where neighbours exist**, the place is kept with `edge_neighbours: {kind: "edge"|"ring-conflict", regions: [...]}` and rule **j** decides each year. The Strait of Messina is the case: Calabria and Sicily are both the Two Sicilies 1816-1861 and Italy from 1861, so a note at Scilla, Bagnara, Reggio or Messina is true on whichever side of the ring the town stands, in those years; in a year the two differ there is no note.
  - `--edge strict` is the old rule (every near-edge place refused); the snapshot's `policy.edge` says which was used.
  - A place far outside its own ring and near no other is kept and counted (`--outside-ring refuse` silences it). A place with **no coordinates cannot be checked**: it is kept, listed in `unchecked_edge`, and counted (`eraAt(...).unchecked` is true), so an archive can say how many of its notes rest on a table entry alone.
- **j. Edge agreement (the library, per year).** For a place in `edge_neighbours`, the note needs, in **every** neighbouring region, in that year: exactly one kept era that covers it; no other era of that region overlapping it (anywhere); no refused era over the year; neither `approx` nor `contested` true, nor null unless the policy allows it; and the **same label** as the place's own era (the display label, compared as written). Anything else is unknown, and unknown is silence: `whyNot` says `edge` (or `ring-conflict`). If the year is not a boundary of the place's own era but is the first year of a neighbour's era, the neighbour's era just before it must exist, be kept and carry the same label (the event may be on either side of that change); a boundary note ("From that year: X") needs only the neighbour's era in force. Where all agree, the note is drawn and says so: `eraAt(...).edgeAgree` is true and the note carries `data-era-edge-agree="1"`. A snapshot entry the library cannot read (no kind, an unknown kind, no regions, the place's own region as a neighbour) is silence.
- **k. The style belongs to a page that has a note.** The component used to carry a scoped style, which Astro bundles into every page that renders the component whether or not it draws a note (+470 KB raw, +193 KB gzip across one 4,000-page archive; +126 KB across another). The note now emits one `<style is:inline data-era-css>` (the rules are `ERA_CSS` in `lib/era.js`: muted, token-driven, as before) from the **first note a page renders**, once per page (`claim(Astro.request, ERA_CSS_KEY)`, the mechanism `Rec.astro` uses for its figure ids), and a page that draws no note carries no era CSS. The `<style>` sits in the flow ahead of that note; a text extractor that reads built HTML must skip `<style>` as it skips `<script>` (the kit's own tools do). The gate fails a page with a note and no style, a style drawn twice, or a style on a page with no note (`css`).

## The snapshot (`era-snapshot.json`, committed by the archive; version 3)

The sites are static and the Atlas's files change daily, so a note cannot fetch. The archive commits a snapshot, refreshes it deliberately with `erasnap.py`, and reviews the diff. Nothing in a build reads the Atlas.

```
version 3, built
contract   { name, version, generated, sha256 }          the contract it was cut from (sha256 of the file's bytes)
atlas      { base, rings_source: contract|file|none, rings_sha256 (the override file's, else null) }
policy     { unassessed: refuse|allow, boundary: newer|silent, recent_from: 1990, edge_km: 15, edge: agree|strict }
regions    { region id: [ {id, from, to|null, present, regime, label, polity, basis, seeded_from_archive, approx, contested,
                           assessed, why|null, url} ] }   (the regions the places use, and the neighbours of the edge places)
places     { folded place: region id }                     fold() of the place as the archive prints it
places_silent  { folded place: edge|marked-edge|ring-conflict }
edge_neighbours { folded place: {kind: edge|ring-conflict, regions: [region id]} }   mapped near an edge: the regions it is held to
unchecked_edge [ folded place ]                            mapped, but no coordinates: the edge rule could not be applied
dropped    [ {region, id, from, to, reason} ]              eras refused (so a count of what was left silent can say why)
quality    { counts: {gaps, overlaps}, gaps: [...], overlaps: [...] }   the contract's own lists, the entries that name a region here
```

An era the contract's `quality` block lists in a gap or an overlap is refused ("listed in the contract's quality gaps/overlaps"; today the lists name flag pages only, never a region era). Two eras of one region that overlap are both kept and both flagged contested: the library stays silent about every year they touch.

The archive's place table is `{place as printed: region id}` (or `{region, lat, lon, edge}`; `null` or `-` says "looked at, no region covers it").

```
python3 node_modules/@daviddef/archive-kit/kit/tools/erasnap.py \
   --contract "<Record Atlas>/site/public/context.json" \
   --places src/data/era-places.json --out src/data/era-snapshot.json [--unassessed allow] [--report drops.json]
python3 .../erasnap.py ... --check      # in CI: the committed snapshot is what the inputs build
```

`--report` writes, per region, how many eras were refused and why (counts only): that is what to send the Atlas session. The old `regions.json`-as-source form of this builder is gone: the contract is the source. **The library and the gate read version 3 only**: a snapshot of version 1 or 2 is refused (a version 2 snapshot would have its near-edge places silent, and the library must not read a version 3 snapshot's mapped near-edge places as if they had been checked), so an archive that takes this kit rebuilds its snapshot with it. Changes to the call: `--rings` is no longer needed (drop it, or keep it as the override), `--edge agree|strict` is new (default agree), and the snapshot carries `atlas.rings_source`, `policy.edge`, `edge_neighbours` and `assessed`/`why` on each era.

## Wiring an archive

```astro
---
import { eraAt, plainYear } from "@daviddef/archive-kit/lib/era.js";
import EraNote from "@daviddef/archive-kit/components/EraNote.astro";
import snapshot from "../../data/era-snapshot.json";
const noNotes = living || meta.noindex;                   // rule c, decided by the page
---
<div class="v">{e.place}{!noNotes && <EraNote era={eraAt(snapshot, e.place, plainYear(e.date, e.year))} />}</div>
```

(The call is the same since version 1; the component draws its own style, once, on a page that has a note, so the archive adds no CSS for it.) After the build, `python3 .../checkera.py --dist dist --snapshot src/data/era-snapshot.json --living-urls <the archive's living list> --require-tracked`. The gate reads the **built** pages: a template that is right can still be given a wrong year. It checks that every `data-era` is an era id the snapshot holds, that `data-era-year` satisfies `from <= year < to`, that the quiet rule and the boundary wording hold, that the label is the snapshot's, that the source words and the era link are the right ones, that `data-era-assessed` says what the snapshot says of the era, that `data-era-edge-agree` is only on a region that has an edge place, that the era style is on every page with a note exactly once and on no page without one, that no note is on a noindex or living page, and that the snapshot is committed. It prints **counts only** (notes on assessed and on unassessed eras, at an edge where every neighbour agrees, on a boundary year, on a seeded region; pages that carry the style). It refuses an empty build and a build with no notes (exit 2): a gate that found nothing has not found that nothing is wrong.

## Counting what was left silent

`whyNot(snapshot, place, year, opts)` returns one of `snapshot`, `year`, `place`, `marked-edge`, `no-region`, `no-era`, `era-refused`, `contested`, `recent`, `boundary`, `approx`, `unassessed`, `no-label`, `bad-id`, `edge`, `ring-conflict`, or `ok`. (`edge` and `ring-conflict` are also what a place refused for every year by the builder gives, first; for an edge place kept with neighbours they come last: only when nothing else would have silenced the year.) An archive that reports "n events, k notes, the rest silent because ..." should call it for every event, with `plainYear` for the year (a date that is uncertain is `year`).

## What this does not do, on purpose

No flag images (the Atlas's SVGs have no licence file), no ruler (one per era, not per year), no language of administration (none exists), no "life in context" strip, no country-level fallback, no live fetch. The label is the Atlas's **regime** label ("Naples / the Two Sicilies", "Italy", "Britain and its colonies"), which is a filing regime named in the Atlas's own words, not always the state's formal name. That is why every note says whose words they are.
