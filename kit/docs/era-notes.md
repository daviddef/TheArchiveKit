# "At the time" notes: who held the ground, from the Record Atlas's context contract

Written 18 October 2026; second version the same day, rebuilt on the Atlas's versioned `context.json` (contract 1.7.0) in place of `regions.json`. Pilot: the Mazza and Falco archives' person pages. Study behind it: the flags coverage study of the same day.

## What it is

Beside a dated place-event on a **deceased** person's page, a small muted line:

> Briatico · 1860 · *· At the time: Naples / the Two Sicilies* per the Record Atlas

It is **context about the ground, never a claim about the family**, it says where it came from, and where the data does not support it there is **nothing**: silence beats a wrong note. Text only: no flag image, no ruler, no language of administration, no "before/after" events, no live fetch.

| Piece | File |
|---|---|
| the rules, pure (no I/O) | `kit/lib/era.js` (`eraAt`, `whyNot`, `plainYear`, `fold`, `eraHref`, `renderEra`) and its Python twin `kit/tools/eralib.py` |
| the note | `kit/components/EraNote.astro` |
| the snapshot builder | `kit/tools/erasnap.py` |
| the gate on a built site | `kit/tools/checkera.py` |
| shared cases (both halves run them) | `kit/data/era-cases.json` (hand-written expectations) |
| tests with a planted fault per rule | `kit/tools/era_logic.mjs` (node), `kit/tools/era_selftest.py` (python) |

## The contract, and what this reads of it

`https://recordatlas.org/context.json` is documented at `/data/#context`. Each region era has a **permanent id** (`<region>--era-<from>`; the note's `data-era` is that id), `from`, `to` (`null` = still running, with `present: true`), `regimeLabel` (the display label), `polity`, `basis` (where the region's bands came from), `contested` and `approx`, and a `url` that lands on the era. The file also has a `rule` (how to look a year up), a `quality` block (gaps and overlaps, where a lookup must stay silent) and `countries` (the flag-page layer). Its `contract.version` is semantic: `erasnap.py` reads **major version 1** and refuses anything else, and records the version, the `generated` stamp and the sha256 of the file in the snapshot.

**Read:** `regions` only. **Not read:** `countries`. That layer is keyed on flag pages, most eras are unreviewed, and a sub-national place needs the sub-national answer; the archive's own place-to-region table decides which region a place is in, and a place no region covers gets no note (the contract's advice to "fall back to countries" is deliberately not taken).

**The rings are not in the contract.** The edge rule needs them, so `erasnap.py` takes them from the Atlas's `regions.json` (use the one in the Atlas repository's `data/`, from which the contract is built; the copy served at `site/public/regions.json` can be older than the contract). It refuses a ring file that describes other regions or other eras than the contract.

## The rules, and why each exists

- **a. Region eras only**, mapped from the place by the archive's table (above).
- **b. The interval is half-open: `from <= year < to`**, as the contract states it. A note needs a place that maps to a region and a year inside exactly one era with a whole-number `from`, a `to` that is a whole number or `null`, and a non-empty **display label**. The label is the contract's `regimeLabel`, never the era's free-text `polity` (which can carry today's province: "Italy - Provincia di Vibo Valentia" for a town that is in Reggio). Two exceptions, both in `erasnap.py`: a regime the Atlas itself calls shorthand rather than a state (`feudal` = "Aquileia · Gorizia · Frankopan", `german` = "German occupation", `--refuse-regimes`) is refused; a regime that is a bare shorthand (`napo` = "Napoleonic", `--qualify-regimes`) is shown with the era's own polity ("Napoleonic — Illyrian Provinces"; "Napoleonic Kingdom of Naples" already begins with the label), and refused where the era has no polity. Nothing is invented. An era outside the dates the ring file holds for its regime (`existed`) is refused.
- **c. Never on a living, held-out or noindex page.** The library cannot know who is living, so the *page* must not call it for them, and `checkera.py` fails the build on a note found on a noindex page, a `data-living` page, or a page in the archive's living list.
- **d. A year on a boundary.** The contract's rule says a year equal to a boundary belongs to the newer era, and `erasnap.py` records `policy.boundary = "newer"` only if the contract's `rule` text says so (otherwise `"silent"`, and a boundary year gets no note; `--boundary silent` makes it stricter, never looser). The contract's own documentation adds that "a consumer holding only a year should say «in that year» or stay silent", and a year-only date cannot say which side of the change the event fell. So a boundary-year note resolves to the newer era (the contract's rule) but is **worded so that it is true either way**: `· From that year: <the newer label> per the Record Atlas`, marked `data-era-boundary="1"`, and checked by the gate. A year is a boundary only where another era (kept or refused) of the same region ends in that year; the first year of a region's first era, or of an era after a gap, is an ordinary year. A date the page marks uncertain ("c. 1860", "before 1860", "1860?") has no year at all: `plainYear(date, year)` gives a year only for "1860", "March 1860", "12 March 1860" or ISO, and only if it agrees with the number the archive holds. (Not handled, said plainly: events before 1752 in England, or in the Julian calendar, where the year begins on a different day. An archive that has them must hand `null`.)
- **e. The link goes to the era**, the contract's own `url` on the Atlas's base (the contract asks for a citation with a link to the era's url), accepted only if it is the path the id implies. `data-era` is the contract's era id.
- **f. Circularity.** An era whose `basis` begins `seeded:` (today `seeded:defranceschi-sovereignty`: istria-central, istria-south, istria-west, kvarner, carnia, dalmatia) was taken from this estate's own research. The snapshot carries `seeded_from_archive` on it and the note says "per this archive's own research". `basis: "unknown"` (imotski: written in the same first batch, never checked) and `not-recorded` ("the file does not say") keep the standard words, and the basis is carried so an archive can count them.
- **g. null is not false.** The contract carries `contested` and `approx` as `null` on a region era when nobody has assessed it. `erasnap.py` **refuses** such an era by default (`--unassessed refuse`, reason "contested or approx not assessed (null)"), and refuses an era marked `true`. The library repeats the rule: an era whose flags are null is silent unless the snapshot's `policy.unassessed` is `"allow"`, and a flag that is neither true, false nor null is read as true. **As of contract 1.7.0 every one of the 347 region eras is null on both, so the default keeps no era at all and an archive built that way has no notes.** `--unassessed allow` is the deliberate, recorded choice to note them anyway: it is written into the snapshot's policy, printed by the gate on every build ("N on an era the Atlas has not assessed"), and `checkera.py --strict-unassessed` refuses it. The right fix is for the Atlas to assess eras; until it does, an archive that allows them is stating, in its own commit, that it accepts the Atlas's dates unassessed.
- **h. The quiet rule.** An event in the era that is still running (`to` null) in or after `recent_from` (default **1990**) gets no note: a modern event teaches nothing. Parameterised: `erasnap.py --recent-from N` writes it into the snapshot's policy and the gate holds the page to it; `eraAt(snap, place, year, { recentFrom: N })` overrides it for one call (`Infinity` switches it off); `eralib.era_at(..., recent_from=N)` the same in Python. It applies only to the running era: a closed era is not "modern".
- **i. Edge.** The rings are 4-11 vertex shapes, "approximate by design". With the place's coordinates, `erasnap.py` refuses a place within `--edge-km` (default **15**) of its own region's ring edge, inside or outside it; a place inside another region's ring and not its own ("ring-conflict"); and a place the archive's table marks `"edge": true`. A place with **no coordinates cannot be checked**: it is kept, listed in `unchecked_edge`, and counted (`eraAt(...).unchecked` is true), so an archive can say how many of its notes rest on a table entry alone. A place far outside its own ring and near no other is kept and counted (`--outside-ring refuse` silences it). The distance is measured in a flat projection around the point (1 degree of latitude is 111.195 km, longitude scaled by cos latitude) to the ring's edges as straight lines between its `[lat, lon]` vertices. Refused places are listed in `places_silent` ("edge", "marked-edge", "ring-conflict") so they can be counted.

## The snapshot (`era-snapshot.json`, committed by the archive; version 2)

The sites are static and the Atlas's files change daily, so a note cannot fetch. The archive commits a snapshot, refreshes it deliberately with `erasnap.py`, and reviews the diff. Nothing in a build reads the Atlas.

```
version 2, built
contract   { name, version, generated, sha256 }          the contract it was cut from (sha256 of the file's bytes)
atlas      { base, rings_sha256 }
policy     { unassessed: refuse|allow, boundary: newer|silent, recent_from: 1990, edge_km: 15 }
regions    { region id: [ {id, from, to|null, present, regime, label, polity, basis, seeded_from_archive, approx, contested, url} ] }
places     { folded place: region id }                     fold() of the place as the archive prints it
places_silent  { folded place: edge|marked-edge|ring-conflict }
unchecked_edge [ folded place ]                            mapped, but no coordinates: the edge rule could not be applied
dropped    [ {region, id, from, to, reason} ]              eras refused (so a count of what was left silent can say why)
quality    { counts: {gaps, overlaps}, gaps: [...], overlaps: [...] }   the contract's own lists, the entries that name a region here
```

An era the contract's `quality` block lists in a gap or an overlap is refused ("listed in the contract's quality gaps/overlaps"; today the lists name flag pages only, never a region era). Two eras of one region that overlap are both kept and both flagged contested: the library stays silent about every year they touch.

The archive's place table is `{place as printed: region id}` (or `{region, lat, lon, edge}`; `null` or `-` says "looked at, no region covers it").

```
python3 node_modules/@daviddef/archive-kit/kit/tools/erasnap.py \
   --contract "<Record Atlas>/site/public/context.json" --rings "<Record Atlas>/data/regions.json" \
   --places src/data/era-places.json --out src/data/era-snapshot.json [--unassessed allow] [--report drops.json]
python3 .../erasnap.py ... --check      # in CI: the committed snapshot is what the inputs build
```

`--report` writes, per region, how many eras were refused and why (counts only): that is what to send the Atlas session. The old `regions.json`-as-source form of this builder is gone: the contract is the source, and a snapshot of version 1 is refused by the library and the gate.

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

(The call is the same as in version 1; only the snapshot and the words of a boundary note change.) After the build, `python3 .../checkera.py --dist dist --snapshot src/data/era-snapshot.json --living-urls <the archive's living list> --require-tracked`. The gate reads the **built** pages: a template that is right can still be given a wrong year. It checks that every `data-era` is an era id the snapshot holds, that `data-era-year` satisfies `from <= year < to`, that the quiet rule and the boundary wording hold, that the label is the snapshot's, that the source words and the era link are the right ones, that no note is on a noindex or living page, and that the snapshot is committed. It prints **counts only**. It refuses an empty build and a build with no notes (exit 2): a gate that found nothing has not found that nothing is wrong.

## Counting what was left silent

`whyNot(snapshot, place, year, opts)` returns one of `snapshot`, `year`, `place`, `edge`, `marked-edge`, `ring-conflict`, `no-region`, `no-era`, `era-refused`, `contested`, `recent`, `boundary`, `approx`, `unassessed`, `no-label`, `bad-id`, or `ok`. An archive that reports "n events, k notes, the rest silent because ..." should call it for every event, with `plainYear` for the year (a date that is uncertain is `year`).

## What this does not do, on purpose

No flag images (the Atlas's SVGs have no licence file), no ruler (one per era, not per year), no language of administration (none exists), no "life in context" strip, no country-level fallback, no live fetch. The label is the Atlas's **regime** label ("Naples / the Two Sicilies", "Italy", "Britain and its colonies"), which is a filing regime named in the Atlas's own words, not always the state's formal name. That is why every note says whose words they are.
