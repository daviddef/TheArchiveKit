# The family ribbon, how our line connects, and the direct-line tint

Three things that belong together, built on the story (`docs/story.md`):

1. **The family ribbon** (`components/FamilyRibbon.astro`): on a family page (Papić, Žubrinić, Zampiello, Sneyd, Kolbe ...), that
   family's own line of generations as the story's ribbon draws ours, smaller.
2. **How our line connects**: under the ribbon, one block for each place the direct line touches this family; or, if it does not,
   one quiet block that says so and what is missing.
3. **The direct-line tint** (`styles/ours.css`, `--ours` / `--ours-soft`, class `is-ours`): wherever a person on our direct line is
   drawn, the card, node, row or band has the tint.

An archive supplies **two data files** and passes them to the components. Everything else is the kit's.

| File | What it is |
| --- | --- |
| `src/data/direct-line.json` | who is on our direct line; **made from the story**, never typed |
| `src/data/family-lines.json` | for each family page: its cards (or the lines.json lane they come from), its status, how our line connects |

| Kit file | What it is |
| --- | --- |
| `components/FamilyRibbon.astro` | the mini ribbon, the connection blocks and their legend |
| `lib/familyribbon.js`, `lib/directline.js` | the logic (cards from a lane, blocks, relations, marriages from the story; who is on the line, the band's words) |
| `styles/familyribbon.css`, `styles/ours.css` | the ribbon and the blocks; the tint, its tokens and every `.is-ours` rule |
| `data/family-ribbon-schema.json`, `data/direct-line-schema.json` | the contracts |
| `data/family-lines-example.json`, `data/direct-line-example.json` | the fixtures (the Ardens of Valmora; they match `story-example.json`) |
| `tools/directline.py` | makes `direct-line.json` from the story, or checks it |
| `tools/checkfamilyribbon.py` | the gate (and `--selftest`, which plants 50 faults) |
| `tools/familyribbon_logic.mjs` | the logic selftest, including the tint's contrast and hue |

## The direct line: `src/data/direct-line.json`

```jsonc
{ "generationLabel": "generation",                       // the noun in the band: "On our direct line · generation 7"
  "people":   [{ "slug": "ljubomir-blazevic", "generation": 7, "storyChapter": "sailor", "name": "Ljubomir Blažević" }, ...],
  "partners": [{ "slug": "milka-lucia-papic", "generation": 7, "storyChapter": "sailor", "partnerOf": "ljubomir-blazevic" }],
  "unlinked": [{ "generation": 9, "storyChapter": "us" }] }
```

* `people`: **one entry for each story ribbon card that has a `person`**, `generation` being the card's number (earliest = 1, as the
  ribbon numbers them; the Spine counts the other way, and the band uses the ribbon's number).
* `partners`: the spouses on those cards who are themselves our ancestors (a mother is). The card says so: `"spouseDirect": true`
  (new, optional, in `story-schema.json`). A spouse who is not an ancestor (a second wife, a daughter-in-law) is not listed and is not tinted.
* `unlinked`: a ribbon card with no `person` page (a living generation the archive has not given one). It is on the line, and is
  tinted as `gen:N`. Better: give it a person page.
* **Make it, do not type it:** `python3 node_modules/@daviddef/archive-kit/kit/tools/directline.py --story src/data/story.json --write src/data/direct-line.json`.
  The gate (D1, D2) fails a file that is not what the story makes, so the tint cannot drift from the story.

## The tint

| Token | Light | Dark | For |
| --- | --- | --- | --- |
| `--ours-soft` | `#e9ebf8` | `#252a47` | the fill of anything on our line |
| `--ours` | `#4a55a8` | `#a5adf0` | the bar along its top edge, the hairline of the pill and the swatch |
| `--ours-ink` | `#2b3275` | `#cdd2fb` | a label on the soft fill |

**Why this hue.** The story already spends colour on the evidence outline (solid accent, dashed gold, dotted grey-brown), the thread
(terracotta) and the glyphs (ochre). The tint is none of those: a cool indigo wash, 233 degrees where they all sit between 10 and 40,
so a reader can name it ("the blue ones are ours"). It is a **fill**, never an outline, so a tinted card still says in its edge how well
its origin is known; and it is never the only cue: a tinted card has a bar along its top, a spouse on the line has a swatch, and the
legend says **tinted = our direct line**. `familyribbon_logic.mjs` holds the contrast (the story's ink, ink-2 and ink-3 read on
`--ours-soft` at 4.5:1 or better, `--ours-ink` at 7:1, `--ours` against the page at 3:1) and the hue (45 degrees or more from each
evidence colour), in both themes. An archive may set `--ours`, `--ours-soft` and `--ours-ink` in its own `:root`; every kit rule that
defines them is `:where()`, so the archive's value wins whatever the order of the stylesheets. Set the dark ones too.

**Where it appears** (pass `directLine={directLine}` to each; nothing is tinted without it):

| Component | What is tinted |
| --- | --- |
| `StoryRibbon` (via `StoryBook`) | every card on the line (`li.st-rb.is-ours`, `data-ours` = the person or `gen:N`) |
| `FamilyRibbon` | a card whose person is in the file; our side of each connection block; a spouse on the line gets a swatch |
| `LineTree` (via `StoryBook`) | the node of a person on the file (`a.is-ours`): the circle is filled, its outline stays its evidence |
| `BranchRivers` | a lane the archive marks `"ours": true` (a tinted band under its colour, `data-ours="lane:<key>"`); a node whose `person` is in the file |
| `Spine` | a row with a `person` slug that is in the file |
| `PersonPage` | a quiet band under the name, **On our direct line · generation n**, with "in the story →"; `PersonChart`'s relatives whose row carries `slug` |

A page with any tinted card, node or row carries the legend `tinted = our direct line` (the components print it).

## The family ribbon: `src/data/family-lines.json`

```jsonc
{ "families": [{
  "id": "papic", "title": "Papić", "page": "/papic/",
  "status": "documented",                                  // documented | inferred | origin-unknown | family-lore (the lines page's four tiers)
  "statusNote": "1857 baptism and 1885 marriage read",
  "span": [1807, null],
  "cards": [ card, ... ],                                   // or:  "lane": { "set": "papic", "key": "senj" }
  "connections": [ connection, ... ],                       // or:  "notConnected": { "why": "..." }
}] }
```

**Card** = the story's card (`name, years, origin, originGrade, spouse, spouseOrigin, atPlace, atYear, living`) plus `person`,
`spousePerson`, `spouseHref`, `title` and, for a living child, `minor: true`. Every card has every field (an empty string where it
does not apply). Earliest first. **The outline is the evidence** for "from <origin>", exactly the story's: solid documented, dashed
inferred, dotted family memory or the family's tree.

**Cards from a lane.** An archive that already draws the family on its lines page (`lines.json`) need not type the cards twice. Give
`"lane": {"set", "key"}` and the page passes `lines` and `people` to the component. `cardsFromLane(lane, people)` (`lib/familyribbon.js`)
makes a card from every lane node that has a `person`; a node without one (a marriage, an inn, a death) is an event, not a generation,
and is not a card (the component says how many it left out). `people` is the archive's own `{slug: {name, years, living, minor, origin,
originGrade, spouse, spouseOrigin, spousePerson, atPlace, atYear}}`; a node whose person is not in it is skipped, never guessed. The
grade of "from" is the node's `evidence` (`read` is documented; `indexed`, `scanned` and `inferred` are inferred; `tree`, `disputed`
and `none` are family lore) or, with none, the lane's own tier. Nothing is promoted.

**The living rule is the story's.** A living card has no years, no `atYear`, and no date in its text; a minor is an initial, no years,
no spouse, no link. The component refuses to print a date for a living card, and the gate (F4, B2) fails the data and the built page.

**Connection** = where OUR direct line touches this family:

```jsonc
{ "ourSlug": "ljubomir-blazevic", "ourGeneration": 7,
  "theirSlug": "milka-lucia-papic", "theirName": "Milka Papić", "theirOrigin": "of Senj",
  "relation": "married", "grade": "doc",
  "storyHref": "/story/#sailor", "note": "The marriage entry of 8 December 1920, Senj." }
```

* `relation` is **our person's relation to theirs**, so a block reads left to right: our person, the relation, their person.
  Ljubomir (ours) **married** Milka Papić; Hedviga (ours) **daughter of** Milka Papić. One of `married`, `son of`, `daughter of`, `child of`,
  `father of`, `mother of`, `parent of`, `brother of`, `sister of`, `sibling of`, `godparent of`, `godchild of`, `witness for`. The last
  three are said only of a documented relation (`grade: doc`); a godparent is in a baptism entry or is nothing.
* `ourSlug` must be in `direct-line.json`, and `ourGeneration` its generation there (the block prints the file's, not yours). `theirSlug`
  is on this family's cards (person or spouse) or is a built person page.
* `grade` is the grade of **the connection**, drawn as the block's outline (solid, dashed, dotted).
* **Derive the marriages.** `marriageConnections(story.ribbon, familyOf)` reads every story card with a person and a spouse as a
  `married` connection for the family that owns the spouse (`familyOf(slug)` is the archive's: which family page). The grade it gives is
  the card's own `originGrade`, the weakest the card admits; an archive that knows better states the connection itself, and its own
  wins (`mergeConnections`). Pass the result as `derived` to the component.
* A family the line does not touch has **`notConnected: {why}`** instead, and the page shows one quiet dotted block, *Not connected to
  our line yet*, with the reason, in the archive's words: what is missing. A family has connections or `notConnected`, never both and never neither.

On the page a card that is one end of a connection carries a small pill, **↔ our gen. 7**, that links to its block.

## Using it

```astro
---
import FamilyRibbon from "@daviddef/archive-kit/components/FamilyRibbon.astro";
import { marriageConnections } from "@daviddef/archive-kit/lib/familyribbon.js";
import familyLines from "../data/family-lines.json";
import directLine from "../data/direct-line.json";
import story from "../data/story.json";
const fam = familyLines.families.find((f) => f.id === family);
const derived = marriageConnections(story.ribbon, (slug) => familyOfPerson(slug))[family] || [];
---
{fam && <FamilyRibbon family={fam} directLine={directLine} derived={derived} personHref={(s) => u(`/people/${s}/`)} u={u} />}
```

Phone: the row scrolls inside its own container (never the page), a card is 116px (128px from 900px), the spouse line shows from 560px,
the connection blocks stack their three parts under 420px.

## The gate: `kit/tools/checkfamilyribbon.py`

```
python3 node_modules/@daviddef/archive-kit/kit/tools/checkfamilyribbon.py --families src/data/family-lines.json --direct src/data/direct-line.json \
        --story src/data/story.json --dist dist [--lines src/data/lines.json] [--living ../private/living.json]
python3 node_modules/@daviddef/archive-kit/kit/tools/checkfamilyribbon.py --selftest
```

The rule codes are in the tool's header. In short: the direct-line file is the story's ribbon (D1-D3); every card has the same fields,
no living card holds a date, no minor is more than an initial (F2, F4); every connection's `ourSlug` is on the direct line, its
generation is right, its `theirSlug` exists, its relation and grade are valid, a family is connected or says why not (C1-C6); every link
resolves (B3, C7); then it **reads the built pages back**: a ribbon for each family with a card per card and the same parts in each,
a block per connection, a card tinted exactly when its person is in the file and saying whom (B4, O1), the story ribbon tinted on every
card on the line and nowhere else (O2), the band on every direct-line person's page and on no other (O3), the legend wherever the tint
is (B6, O4). `--selftest` plants the faults one at a time in `family-lines-example.json` and requires each to be caught under its own code.

`package.json`: `"check:family": "python3 node_modules/@daviddef/archive-kit/kit/tools/directline.py --story src/data/story.json --check src/data/direct-line.json && python3 node_modules/@daviddef/archive-kit/kit/tools/checkfamilyribbon.py --families src/data/family-lines.json --direct src/data/direct-line.json --story src/data/story.json --dist \"${ARCHIVE_OUT:-dist}\" && python3 node_modules/@daviddef/archive-kit/kit/tools/checkfamilyribbon.py --selftest"`, after `check:story` in the build.
