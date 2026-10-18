# "At the time" notes: who held the ground, from the Record Atlas

Written 18 October 2026. Pilot: the Mazza archive's person pages. Study behind it: the flags coverage study of the same day (every number below that is about the eight archives comes from it).

## What it is

Beside a dated place-event on a **deceased** person's page, a small muted line:

> Briatico · 1860 · *· At the time: Naples / the Two Sicilies* per the Record Atlas

It is **context about the ground, never a claim about the family**, it says where it came from, and where the data does not support it there is **nothing**: silence beats a wrong note. Text only: no flag image, no ruler, no language of administration, no "before/after" events, no live fetch.

| Piece | File |
|---|---|
| the rules, pure (no I/O) | `kit/lib/era.js` (`eraAt`, `whyNot`, `plainYear`, `fold`, `regionHref`, `renderEra`) and its Python twin `kit/tools/eralib.py` |
| the note | `kit/components/EraNote.astro` |
| the snapshot builder | `kit/tools/erasnap.py` |
| the gate on a built site | `kit/tools/checkera.py` |
| shared cases (both halves run them) | `kit/data/era-cases.json` |
| tests with a planted fault per rule | `kit/tools/era_logic.mjs` (node), `kit/tools/era_selftest.py` (python) |

## The rules, and why each exists

The Atlas has two era layers. The country flag timelines are keyed on **modern** countries; the record regions (`regions.json`, 42 sub-national regions, each a short list of eras with a `regime` id, a free-text `polity` and the archives its paper went to) are not. The study resolved real events through both and found the country layer wrong exactly where a note matters (a place in today's Croatia in 1925 resolves to the Kingdom of Serbs, Croats and Slovenes, though Istria was Italian; Briatico in 1860 resolves to Sardinia, though it was in the Two Sicilies), merging four British timelines into one, nine countries with concurrent eras, holes, and a "ruler" that is the first ruler of the era, not of the year.

- **a. Region eras only.** Never a country-level lookup. The place-to-region table is the **archive's** (it knows its own places); the Atlas only supplies the eras.
- **b. A note needs** a place that maps to a region **and** a year inside exactly one era with a whole-number start and end year, not marked approximate, not contested (no other era of the region overlaps it), and with a **regime label** that is a non-empty string. The label is `regimes[era.regime].label`, never the era's `polity` string, which can carry today's province ("Italy - Provincia di Vibo Valentia" for a town that is in Reggio). `erasnap.py` also refuses a regime the Atlas itself calls shorthand rather than a state (`feudal` = "Aquileia · Gorizia · Frankopan", `german` = "German occupation"): the label is Istria's and says nothing about Calabria. An era outside the dates the Atlas holds for its regime is refused.
- **c. Never on a living, held-out or noindex page.** The library cannot know who is living, so the *page* must not call it for them, and `checkera.py` fails the build on a note found on a noindex page, a `data-living` page, or a page in the archive's living list.
- **d. A year on an era boundary gets no note** (a year-only date cannot say which side it is on), and neither does a date the page marks uncertain: `plainYear(date, year)` gives a year only for "1860", "March 1860", "12 March 1860" or ISO, and only if it agrees with the number the archive holds. "c. 1860", "about 1860", "before 1860", "after ...", "between ...", "1860?" give none. (Not handled, said plainly: events before 1752 in England, or in the Julian calendar, where the year begins on a different day. The Mazza pilot has none; an archive that does must hand `null` for them.)
- **e. The link** goes to the Atlas's page for the **region** (`/region/<id>/`). The Atlas has no stable deep link to a region era (the era anchors it publishes belong to the flag pages, which are country-level), so none is made up. Region ids are the Atlas's own and every region has that page. The note says "per the Record Atlas".
- **f. Circularity.** The Atlas seeded the regimes of Istria, Kvarner, Dalmatia and Carnia (and Imotski, which sits in Dalmatia) from the Defranceschi archive's own `sovereignty.json`. A note there would be the estate quoting itself back as a second source. The snapshot carries `seeded_from_archive` per era (`erasnap.py --seeded`) and the note then says "per this archive's own research". Irrelevant to Mazza; present so a later archive does not have to retrofit it.

## The snapshot (`era-snapshot.json`, committed by the archive)

The sites are static and the Atlas's files change daily, so a note cannot fetch. The archive commits a snapshot, refreshes it deliberately with `erasnap.py`, and reviews the diff. Nothing in a build reads the Atlas.

```
version 1, built, atlas_commit_or_etag, atlas {base, file_sha256}
regimes  { regime id: label }                     only the regimes the kept eras use
regions  { region id: [ {from, to, regime, approx, contested, seeded_from_archive, sources} ] }
places   { folded place: region id }              fold() of the place as the archive prints it
dropped  [ {region, from, to, reason} ]           eras the builder refused (so a count of what was left silent can say why)
```

`approx` and `contested` are kept and flagged, not removed: the library then stays silent about every year the era touches, and the archive can say how many events were left silent for that reason. Two eras of a region that overlap are **both** marked contested.

The archive's place table is `{place as printed: region id}` (or `{region, lat, lon}`; `null` or `-` says "looked at, no region covers it"). With coordinates, a place that falls inside **another** region's ring and not its own is refused: the rings are four- and five-sided shapes, "approximate by design", and a town on a ring's edge (Reggio Calabria falls in the Sicily ring) must not be given its neighbour's era. A place that falls in no ring is kept; the archive's table is its own statement.

```
python3 node_modules/@daviddef/archive-kit/kit/tools/erasnap.py \
   --atlas "<Record Atlas>/site/public/regions.json" --places src/data/era-places.json --out src/data/era-snapshot.json
python3 .../erasnap.py ... --check      # in CI: the committed snapshot is what the inputs build
```

Use `site/public/regions.json` (what the Atlas serves; the same bytes as https://recordatlas.org/regions.json), not `data/regions.json`.

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

and, after the build, `python3 .../checkera.py --dist dist --snapshot src/data/era-snapshot.json --living-urls <the archive's living list> --require-tracked`. The gate reads the **built** pages: a template that is right can still be given a wrong year. It checks that every `data-era` (`<region>--<from>`) is an era the snapshot holds, that `data-era-year` lies strictly inside it, that the label is the snapshot's label for the regime, that the source words and the link are the right ones (and "this archive's own research" where seeded), that no note is on a noindex or living page, and that the snapshot is committed. It prints **counts only**. It refuses an empty build and a build with no notes (exit 2): a gate that found nothing has not found that nothing is wrong.

## Counting what was left silent

`whyNot(snapshot, place, year)` returns one of `snapshot`, `year`, `place`, `no-region`, `era-refused`, `no-era`, `boundary`, `contested`, `approx`, `no-label`, or `ok`. An archive that reports "n events, k notes, the rest silent because ..." should call it for every event, with `plainYear` for the year (a date that is uncertain is `year`).

## What this does not do, on purpose

No flag images (the Atlas's SVGs have no licence file; linking is safe, embedding is David's and the Atlas's decision), no ruler (the Atlas has one ruler per era, not per year: Umberto I's reign is shown as Victor Emmanuel II's), no language of administration (the Atlas has none), no "life in context" strip, no country-level fallback, no live fetch. The Atlas session has been asked for what would let these follow (`atlas-requests.md` in the audit briefs).

The label is the Atlas's **regime** label ("Naples / the Two Sicilies", "Italy", "Britain and its colonies"), which is a filing regime named in the Atlas's own words, not always the state's formal name. That is why every note says whose words they are.
