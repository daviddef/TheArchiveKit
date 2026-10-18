# The book: the whole site as one story, woven on a spine

David, 17 October 2026: *"use the entire site, across all menus … connect them all in a storyline. They are woven together as a book spine."*

Seven menus group an archive's pages by **kind**. The book groups every page by **the story** (where they came from, the
grandparents, the crossing, how the lines join, everyone, how we know). Nothing moves and no address changes; the menus stay as shortcuts.

## One file per archive: `site/src/data/book.json`
```json
{ "title": "The Mazza Archive",
  "front": { "label": "Front matter", "chapters": [ { "path": "/", "title": "The cover", "blurb": "" } ] },
  "parts": [ { "id": "where-from", "numeral": "I", "title": "Three towns on a strait", "intro": "One short paragraph.",
               "flags": "🇮🇹", "hue": "#d9776a",
               "chapters": [ { "path": "/atlas/", "title": "The Atlas", "blurb": "one line", "group": "optional sub-heading" } ] } ],
  "inherit": { "/people/": "/people/", "/who/": "/who/" },
  "outside": [ "/search/" ] }
```
The order is: front matter, then each part's **opener** (`/part/<id>/`, generated) and its chapters. Previous / Next follow it across the whole site.
`inherit` says that a page under a prefix (a person, a name) belongs to the chapter of its index and links back to it instead of having a Previous/Next.
`outside` lists pages that are deliberately not chapters (Search); it is read before `inherit`, so a page listed there stays outside even under an inherited prefix. `/contents/` is the book's own table and needs no entry. A redirect stub (a tiny page, under 1,500 bytes, that only carries a meta refresh) needs no entry either: the check sets it aside and fails only if its target is not built.

## Components (kit/components)
- `BookHead` (once in the layout, below the header): running head (part, chapter n of N, link to the part opener), progress rail in the part's colour, Previous / Next (with the next chapter's title on wide screens) and the Contents link at the top, so a reader can turn the page without scrolling to the foot.
- `BookFoot` (once in the layout, above the site footer): Previous / Next; an inherited page links back to its chapter.
- `BookContents` (page `/contents/`): the whole spine with each chapter's one line.
- `BookPart` (page `/part/[id]/`, `getStaticPaths` over `book.parts`): the opener: the part's paragraph, an optional picture in the default slot, the chapters, "Start reading".
Each takes `book` and the archive's `u` helper and reads the page's own path; no page passes anything.

## Gates
- `node kit/tools/book_logic.mjs`: the order and placement rules, held to `kit/data/book-cases.json`, with planted faults.
- `python3 kit/tools/checkbook.py --dist dist --book src/data/book.json`: reads the BUILT site. Fails on a page nobody placed, a chapter or opener with no built page, a path in the book twice, a missing or wrong running head, a Previous/Next (in the head or the foot) that differs from the book's order, a redirect stub whose target is not built, and an empty build. `checkbook_selftest.py` plants a fault for each.
Wire `checkbook.py` into the archive's build chain after the build. A page that is not in the book fails the build.

## Rules for the writing
Chapter titles and blurbs are taken from the pages' own titles and descriptions. A part's intro is one paragraph assembled from what the part already says on the site: **no new claim about the family**. Never name a living person in a blurb.
