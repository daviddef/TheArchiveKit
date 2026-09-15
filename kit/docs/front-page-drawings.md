# The three front-page drawings

Each archive's front page carries up to three pictures. Two of them need data
only that archive's session can write, and this is the spec for both — kept here
rather than in a chat or a published page, because those are the two places that
do not survive.

| | place picture | sovereignty | rivers |
|---|---|---|---|
| Defranceschi | not used — has rivers | yes | yes |
| Falco | blocked: all 13 places have `n: 0` | needs data | Tributaries, its own |
| Booyzen | yes | needs data | needs data |
| D'Arcy | yes | needs data | needs data |
| Blažević | yes | yes (wired 15 Sep 2026) | needs data |
| Mazza | yes | needs data | needs data |
| Lerena | yes | needs data | needs data |

## The place picture — `PlaceSpark`

Needs nothing written. It reads `public/atlas-data.json` and draws a point per
place, sized by how many people stand in it.

It is a **plot, not a map**: no tiles, no coastline, no borders, because an
archive that has not got a coastline should not draw one. What it was missing
was never geography — it was *names*, which were already in the data beside a
count and the archive's own `cat` grouping. The largest places are labelled and
the dots take their colour from those groupings.

The frame is the tightest window that keeps the most places legible, chosen at
build time from three candidates; anything outside it is drawn **on** the edge
it went out through, as a hollow half-dot, and counted underneath. A place
beyond the frame is shown at the boundary in its own direction, which is a true
statement about it.

**If it renders nothing useful, check your `n` values.** Falco has thirteen
places all at `n: 0`, so there is nothing to size or rank by.

## The sovereignty timeline — `SovereigntyTimeline`

`site/src/data/sovereignty.json`, rendered `<SovereigntyTimeline sov={sov} events={true} />`.

```json
{
  "scale":   { "from": 1600, "break": 1800, "to": 2026, "note": "why the axis breaks" },
  "regimes": { "venice": { "label": "Republic of Venice", "color": "--r-venice" } },
  "lanes":   [ { "label": "Senj", "note": "which families",
                 "bands": [[1617, 1881, "frontier", "Habsburg Military Frontier"]] } ],
  "events":  [ { "year": 1717, "text": "this family's own dated event" } ],
  "world":   [ [1605, "what they were living through"] ]
}
```

Two rules the shape is strict about, and both are why one archive's file sat
inert for weeks after somebody wrote it:

- bands are `[from, to, regime-key, label]` — **not** `[key, from, to]`
- `world` is `[year, text]` pairs — **not** `{year, text}` objects

Every regime key used in a band must exist in `regimes`, or the build dies on an
undefined colour. The lanes are districts this family actually lived in: the
regime dates are public history, but *which* districts matter, and what the
family lived through, is the archive's own work.

## The rivers diagram — `BranchRivers`

`site/src/data/rivers.json`, rendered `<BranchRivers rivers={rivers} />`.

```json
{
  "lanes": [
    { "key": "carnia",
      "colour": "var(--accent)",
      "label":  "Out of Carnia, for work",
      "href":   "/story/",
      "read":   "Nine chapters →",
      "conf":   "documented",
      "nodes": [
        ["Mione", "1679", "What the archive can show happened to this family at
          this place in this year, and what it cannot. **Bold** allowed."]
      ],
      "ends": "Where this branch ended up, in a few words" }
  ],
  "unplaced": [],
  "loose":    []
}
```

`unplaced` is for households of the name that are real and documented and are
**not** on any lane, so the picture cannot quietly imply that everything has
been placed. `loose` is single records not yet attached to anything.

Start from the regions already in your `atlas-data.json` — those groupings *are*
your branches. **But the node paragraphs are research writing and must be
yours.** Do not generate them from the place records: a lane with derived
geometry and empty prose is a confident-looking drawing that says nothing, on
sites whose whole argument is that a claim carries its evidence. A lane with
nothing to say should not be drawn.
