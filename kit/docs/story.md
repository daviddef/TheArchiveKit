# The family story

A short book, told in narration, with a small family tree and a map in each chapter: one page per archive, at `/story/`.
It was built first in the Defranceschi archive (`/story/`, "Down from the Hill"). Everything that is not about that family
is in the kit, so another archive supplies **data** and nothing else.

```astro
---
import Base from "../layouts/Base.astro";
import StoryBook from "@daviddef/archive-kit/components/StoryBook.astro";
import book from "../data/story.json";
import { u } from "../lib/url.js";
const personHref = (slug) => u(`/people/${slug}/`);   // wherever this archive keeps a person's page
---
<Base title={book.title} eyebrow={book.eyebrow} dek={book.dek}>
  <StoryBook book={book} personHref={personHref} u={u} />
</Base>
```

`StoryBook` also takes `md` (the archive's own light-markup renderer, if it already renders links; default the kit's `md()`
with links done by the kit), `Plates` (the archive's plates component, called as `<Plates ids={[...]} />`) or `plateIndex`
(`{id: {src, w, h, title, holder}}`, drawn as plain figures with the id `plate-<id>` so a paragraph can link to one).
The archive's layout draws the title, eyebrow and dek; the component draws everything under them.

## What is in the kit

| File | What it is |
| --- | --- |
| `components/StoryBook.astro` | the page body: ribbon, legend, contents grid, prologue, chapters, "what we do not know", "read the papers", the world notes |
| `components/StoryRibbon.astro` | the generations as a row of equal cards |
| `components/LineTree.astro` | one household as a small tree on a stem, with the thread to the next chapter |
| `components/StoryMap.astro` | one map: coast, places, legs, and the legs listed as text |
| `styles/story.css` | tokens only (`--st-*` read from the archive's own `--ink`, `--accent`, ...), light, dark and phone |
| `lib/story.js`, `lib/mapgeom.js`, `lib/storymap.js` | the logic (grammar, tree layout, projections, clipping, which coastline) |
| `data/story-schema.json` | the contract as JSON Schema |
| `data/story-extents.json` | named map extents: a box and a projection each |
| `data/story-basemap.json` | the coast and borders for those extents, simplified; **Natural Earth 1:50m, public domain** (naturalearthdata.com), through `outlines.json`; written by `tools/storybasemap.mjs --write` |
| `data/story-example.json` | a complete valid story for an invented family; the gate's fixture |
| `data/story-cases.json` | cases both the JS and the Python answer (what a date is, an initial, an extent) |
| `tools/checkfamilystory.py` | the gate. (`checkstory.py` is older and checks the children's site; do not confuse them.) |
| `tools/story_logic.mjs` | the logic selftest |

## The contract, in five lines

1. **Ribbon**: one card per generation, all the same fields: `name, years, origin, originGrade, spouse, spouseOrigin, atPlace, atYear, living` (and `chapter`, the card's link). Empty string where a field does not apply.
2. **Chapters**: `id, numeral, title, place, years, paragraphs[{text, grade doc|inf|lore, register people|world, worldSource archive|history, evidence[], tbc}], tree, quote{text, source}, hardLimit, plates[], papers[]`; every chapter ends with at least one `papers` link.
3. **Tree**: `rows` of kind `above | couple | children | grandchildren | gap`, each node `{id, name, years, grade, person}` or `{living, minor}`; `thread` names the node who carries the line on. A node in a `grandchildren` row carries `of`, the id of its parent in the children row above (see "Whose child" below).
4. **Maps**: `{id, title, extent, chapter, places[{id, name, lat, lon, chapter}], legs[{from, to, grade, years, chapter, routeKnown}]}`; `extent` is a name or a box.
5. **Closing**: `{unknown{items}, papers{links}, after?, notes?, mapNote?}`, and `conflicts[{chapter, note}]` where two of the archive's own sources disagree.

`data/story-schema.json` is the authority for every field, its type and what is required. `data/story-example.json` is the
quickest way to see them all.

## Whose child: `of`

A tree is rows, and a row of grandchildren by itself does not say which child each belongs to. So **a node in a `grandchildren`
row says whose it is**: `of: "<id of its parent in the children row above>"`.

```json
{ "kind": "children", "nodes": [{ "id": "cristina", "name": "Cristina", "living": true }, { "id": "stefanie", "name": "Stefanie", "living": true }] },
{ "kind": "grandchildren", "nodes": [
  { "id": "a", "name": "A.", "living": true, "minor": true, "of": "cristina" },
  { "id": "m", "name": "M.", "living": true, "minor": true, "of": "cristina" },
  { "id": "r", "name": "R.", "living": true, "minor": true, "of": "stefanie" } ] }
```

* **Drawing.** Each group hangs under its own parent, straight below that child: a short stem from the child's own node, the
  grandchildren ticked off it, in the same outlines (solid, dashed, dotted; living filled; minors by initials). A child with no
  children has no stem, so a children row where only some have descendants reads correctly. The thread still runs to the child
  who carries the line.
* **Text.** The picture's description says "Cristina's children: A., M." for each group, and each group is a labelled
  `<g role="group" data-of="cristina">` in the SVG.
* **Gate.** `T4` fails a grandchildren row that follows a children row of **more than one** node when any grandchild has no `of`
  (the drawing would otherwise have to guess, and a wrong guess states a wrong family relationship). `T5` fails an `of` that names
  no node in the children row above, or sits on a node outside a grandchildren row. `V7` reads the built page back and fails a
  grandchild hung under another parent.
* **Backward compatible.** With exactly one child, `of` may be left out: every grandchild is that child's. With several children
  and no `of` the old data still draws (under the child who carries the thread, else the last) but the gate fails it; add `of`.

## The evidence grammar

One vocabulary, in the paragraph marks, the trees and the maps:

| Grade | Means | Paragraph mark | Tree node, ribbon outline | Map leg |
| --- | --- | --- | --- | --- |
| `doc` | a document says so | `doc` | solid | solid |
| `inf` | the archive reasons it from documents | `inf` | dashed | dashed |
| `lore` | family memory, a family chart or tree | `lore` | dotted | dotted |

* A paragraph about **the people** has one grade, **the grade of its weakest claim**, and `evidence` linking to where it can be
  checked. A `doc` paragraph that links to no document is an error.
* A paragraph about **the world around them** (`register: "world"`) is the place, the years, the trade, the neighbours:
  never a claim that these people did or saw it. It is set in apart under "In the world around them", it carries
  `worldSource` (`archive`: this archive's own pages; `history`: general history, to be listed in `closing.notes`) and a link.
* `tbc` on a paragraph says why a claim is still to be confirmed; the page prints "to be confirmed" after it. `conflicts`
  are the same for a disagreement between sources, shown under the chapter. Nothing is silently resolved.
* **A route nobody knows is not drawn.** `routeKnown: false` keeps the leg in the list under the map ("route not known") and
  draws no line: a line says someone went that way.

## The living rule

The story follows the archive's living rule (`living.md`: anyone 80 or younger with no death recorded is living).

* A node flagged `living: true` carries **no years** and no date in its name. It is drawn filled, with a first name or the word
  "living". A ribbon card flagged `living` carries no years and no `atYear`. The components refuse to print a date for them
  even if the data holds one; the gate fails the data that does.
* A **minor** (`minor: true`, and `living: true`) shows **initials only** (`A.`, `M.`), no years, and no link to a page.
* A country, not a town, places the living generations on a map: `{country: true, living: true}`, and a leg that touches one
  carries no years.
* No paragraph, card or note may name a living person within a hundred characters of a date. The gate knows the living from the
  story's own flags and, with `--living`, from the archive's private list of names.

## Maps

A map's `extent` is `"europe"` (a name in `story-extents.json`), `{"preset": "europe", "projection": "mercator"}`, or a box
written out: `{"west": 12, "east": 15, "south": 44.9, "north": 46.7, "projection": "equirectangular"}`. Every place must lie
inside it (the gate checks). Projections: `equirectangular` (default: x scaled by the cosine of the middle latitude),
`plate-carree`, `mercator`. Named extents: world, europe, mediterranean, british-isles, southern-africa, australasia,
south-america-cone. To add one, put it in `story-extents.json` and run `node kit/tools/storybasemap.mjs --write`; a box
that is not a name is drawn from the 50m outlines directly, so a county needs no entry. Place coordinates are the archive's own
gazetteer's; one place id has one set of coordinates on every map.

## Text

Paragraph text is light markup: `*italic*`, `**bold**`, `«quoted»`, and links `[words](/path/#anchor)`, `[words](person:slug)`
(a person's page, through the archive's `personHref`), `[words](#anchor)` on this page. An internal link must resolve in the built
site (the gate checks it).

## The gate

```
python3 node_modules/@daviddef/archive-kit/kit/tools/checkfamilystory.py --story src/data/story.json --dist dist --person-base /people/ --living ../private/living.json
python3 node_modules/@daviddef/archive-kit/kit/tools/checkfamilystory.py --selftest
```

The rule codes are listed in the tool's own header. In short it checks the data against the schema; unique ids and chapter
references; a grade on every paragraph and a source on every world paragraph; every chapter's papers links; every ribbon
card's fields; the living rule on nodes, cards, minors, maps and prose; every place inside its extent, every leg's endpoints,
one coordinate per place; every person and internal link against the built site; and then **reads the built page back**,
independently of the component: the chapters in order, each paragraph with the grade or source the data gives it, a ribbon card
per generation with the same parts, no date on a living node, every grandchild in the group of its own parent, every map dot inside its picture. `--selftest` plants some seventy faults
in `story-example.json`, one at a time, and requires each to be caught under its own code; `node kit/tools/story_logic.mjs`
holds the small rules to cases shared with the gate.

## What an archive supplies

* `src/data/story.json` (the contract above). Nothing else is needed for the page.
* A page `src/pages/story.astro` as above, and `personHref` for its person pages.
* For the plates: its own plates component (`Plates`) or a `plateIndex`.
* For the gate: the `check:story` script above, in the build after `check:links`; the archive's private living list if it has one.
* For the build to be clean: the archive's own gates still apply to the page (the prose and living-year gates read the built HTML).

## Proved on

The Defranceschi story data (8 chapters, 8 ribbon cards, 4 maps) converted to this contract by a one-off script and built in the
Luwinski archive's site: ribbon, legend, contents, trees and maps measure the same as the live page at 1440 and 390 wide in
light and dark, and the gate passes against the built output.
