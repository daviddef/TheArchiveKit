# The lines page: one drawing, one contract, one gate

The rivers drawing (`kit/components/BranchRivers.astro`) shows each line of descent of a surname as a **lane**: a
heading, a status, dated places along it, branches out to destinations, a link to where it is argued. Under the
lanes it shows what is **not** on any lane, in **pens**. Defranceschi's `/lines/` was the best of the eight archives'
because it said, for every lane, how far its evidence reaches, and for every pen, what is in it and why. This is that,
as a contract every archive can fill, and a gate that holds the data to it.

Everything below is optional. Data written for the older component draws as it did; the gate is what asks for more.
The words are made in `kit/lib/lines.js` (`statusLine`, `pensOf`, `penCount`, `ledger`), so two lanes that mean the same
say the same in every archive.

## The file

A drawing is one object. A file may hold one drawing, `{ "sets": [drawing, ...] }` (Luwinski, Blazevic: one drawing per
surname) or a list of drawings.

```jsonc
{
  "title": "Seven families of one surname, and the road each of them took",   // the figure's accessible name
  "caption": "...",                    // the archive's own words under the figure
  "unplacedAfter": "carnia",           // optional: the pens sit under this lane, not at the foot
  "lanes":   [ lane, ... ],
  "pens":    [ pen, ... ],
  "bridges": [ { "from": "carnia", "to": "Rijeka", "conf": "inf", "label": "...", "href": "/fiume-1626/#jbaptista" } ]
}
```

### A lane

```jsonc
{ "key": "svetvincenat", "colour": "var(--accent)", "label": "Svetvinčenat, the castle the name never left",
  "href": "/places/svetvincenat/", "read": "The Svetvinčenat page →",
  "status": "inferred",                                  // documented | inferred | origin-unknown | family-lore
  "statusNote": "origin inferred Carnian",               // the words after the tier
  "span": [1628, 1791],                                  // first and last DOCUMENTED year; last may be null
  "members": ["elena-1628"],                             // people on this line that are not a node
  "nodes": [ node, ... ], "ends": [ end, ... ] }
```

**What a status means.** It is how far back the lane's *evidence* reaches, not how interesting the lane is.

| status | means | printed as (small capitals under the lane title) |
|---|---|---|
| `documented` | every step, its beginning included, rests on a document | `Documented 1628–1791` |
| `inferred` | documented over `span`; where it came from is inferred, and the note says to what | `Documented 1628–1791 · origin inferred Carnian` |
| `origin-unknown` | documented over `span`; where it came from has not been found | `Documented from 1628 · at Ližnjan from 1815 · origin still not found` |
| `family-lore` | nothing on it is documented; it is told, not read. **No span.** | `Family lore · not documented` |

With a note, the note replaces the default words (`origin inferred`, `origin not found`, `not documented`); on a
`documented` lane it is added. With no span, the word *Documented* is not claimed. Each tier also draws a mark
(solid, half, open, dotted ring) and the spine's left end: an inferred lane has a dotted lead-in, an origin-unknown lane
a dashed one ending in an open ring, a family-lore lane a dashed spine. A reader sees the tier without reading it.
The old free string `conf` is drawn only when a lane has no `status`; beside a status it is ignored (and the gate warns).

### A node (a dot on the lane)

```jsonc
[ "Pula", "1659", "why it is here" ]                                   // the old form, still read
{ "place": "Pula", "year": "1659", "why": "...", "person": "/people/ada-1659/", "evidence": "read" }
```

`person` is a person page (a slug, built under `personBase`, default `/people/`; or a path). The dot then links **to the
person**, not to the top of a page. `evidence` is one of the person page's source words (`read`, `indexed`, `scanned`,
`tree`, `inferred`, `disputed`, `none`): anything that is not `read` is drawn hollow and dashed, like a soft ending, and
the reading panel says what it rests on. A trailing `?` on an end's name still means a soft ending.

### A pen

```jsonc
{ "id": "unplaced", "kind": "not-yet-placed",            // not-yet-placed | different-stock
  "head": "Real households of the name — not yet placed on any of these lines",   // optional: a default per kind
  "note": "Why they are in a pen and what would move them out.",                    // printed under the pen
  "items":   [ ["Rijeka — Fiume, Vitipolis", "/carlos-letter/", "why"], ... ],      // households, drawn as dots
  "members": [ "lucia-1844", { "person": "tommaso-pomer", "reason": "read end to end" } ],   // people in the pen
  "count": 2 }                                                                      // people; = members.length
```

The heading prints a count **derived from the data**: `· 8 households · 31 people` (a different-stock pen says
`· 3 kept apart`). The note is printed under the pen, wrapped. The members are listed under the drawing, each a link
to a person page. A pen with neither items nor members is **not drawn**: an empty heading says the archive looked and
found nothing, and nobody has said so. `unplaced` / `loose` / `unplacedHead` / `looseHead` / `looseNote` (and the new
`unplacedNote`) still work and become the two pens; when `pens` is present they are ignored.

`not-yet-placed` is real, documented households of the name that belong to no lane yet. `different-stock` is a
different stock of a common name, kept apart on purpose. They are not the same claim and are not drawn the same way.

### Props

`<BranchRivers rivers={drawing} title caption personBase="/people/" names={{ slug: "Display name" }} />`.
`names` gives the member lists readable names; without it the slug is read as a name. A page that wants to print a count
should take it from `ledger(drawing)` (`lanes`, `tiers`, `households`, `otherStock`, `bridges`, `peopleOnLanes`,
`peopleInPens`) and never type it.

## What the reader gets

- the status line and mark under every lane title; the people counted on it ("14 people on this line");
- every dot a button with an `aria-label`; **Tab** shows it (the reading panel is `aria-live`), **Enter** or **Space**
  goes there; a visible focus ring; a "Skip the drawing" link; the SVG is a labelled group with a `<desc>` that says the
  counts;
- counted pen headings with the pen's note beneath; the people of each pen and lane in `<details>` lists under the drawing;
- under 700px the drawing is replaced by the list: every lane with its status mark, people count and nodes (linked to
  persons), every pen with its count, items and note;
- light and dark come from the archive's own tokens (`--ink`, `--panel`, `--accent`, ...); lane colours are the archive's.

## The gate: `kit/tools/checklines.py`

```
python3 node_modules/@daviddef/archive-kit/kit/tools/checklines.py --lines src/data/lines.json --dist dist \
        [--config standard.json] [--living ../private/living.json]
python3 node_modules/@daviddef/archive-kit/kit/tools/checklines.py --selftest
```

`package.json`:

```json
"check:lines": "python3 node_modules/@daviddef/archive-kit/kit/tools/checklines.py --lines src/data/lines.json --dist dist --config standard.json --living ../private/living.json && python3 node_modules/@daviddef/archive-kit/kit/tools/checklines.py --selftest"
```

Run it after `astro build` and after the autolink step (it reads built pages). An archive that has not migrated yet adds
`--allow-legacy` (a lane with no status is then a warning) and removes it when done.

| code | fails when |
|---|---|
| S1 | no lanes; a lane with no key, label, colour, or href and read text; a key used twice |
| S2 | a lane has no status, or one that is not a tier |
| S3 | a family-lore lane has a span; a span runs backwards; the printed status line is over the limit; (warn) an inferred lane does not say to what; (warn) `conf` beside a status |
| S4 | (warn) a node's year is outside the lane's span: a stale span |
| P1 | a `person`, member, or item person does not resolve to a built page (or its `#fragment` is not in it: H2) |
| P2 | a member is listed twice |
| P3 | a member is on the `--living` list |
| E1 | a person is on more than one lane or pen of a drawing (`lines.exclusive`, default true) |
| K1 | a pen of an unknown kind, or a heading over nothing |
| K2 | a pen's `count` is not its members; (K3, warn) a count with no members cannot be checked; (K4, warn) a pen with households has no note |
| T1 | a number in the chart's own `title` is not a count the data can state (lanes, households, kept apart, bridges, people) |
| T2 | (warn) the same for a number beside *households / families / lanes / joins* in the caption |
| B1 | a bridge names no lane and no unplaced household |
| H1, H2 | an internal href does not resolve to a built page, or its `#fragment` is not an id in it |
| N1 | a node's evidence is not one of the source words |

Exit 0 clean (warnings do not fail), 1 on any error, 2 when it cannot read its input or when nothing was checked. It
prints the number of drawings it looked at, and says when links were not resolved (`--no-dist`). It checks **links as the
data holds them** (`data-href` as well as `<a href>`), which the kit's link check cannot see.

Settings, in the `lines` key of the config file: `exclusive` (true), `sharedAllowed` (slugs that may stand on two lanes: each a
stated exception), `personBase` (`/people/`), `requireStatus` (true), `maxStatusLine` (100), `titleNumbers` (true).

**What the gate cannot do.** It cannot tell whether a status is *right*. It holds the archive to its own statements: that
every lane states one, that the numbers printed are the numbers held, that nobody stands in two places, and that every link
lands. Deciding that a lane is `inferred` and not `documented` is research.

**Living people.** A pen's members are people. Never list a living person: pass `--living` and P3 fails the build, and the
living gate (`living_rule`, the archive's own) still reads the built page.

## Tests

`npm test` runs `kit/tools/lines_logic.mjs` (the words, the pens, the layout arithmetic against what the older component
drew, shown to fail when the arithmetic is broken) and `checklines.py --selftest` (a clean fixture passes; each of 32
faults is planted alone and must fail with its own code). `kit/data/lines-cases.json` is read by both, so the drawing and
the gate give a lane the same words.
