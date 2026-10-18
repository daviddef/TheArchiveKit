# Autolink: every name that resolves is linked, and the number cannot get worse

David, 18 October 2026: *"why do so many names on our narrative pages have no link to their person page?"* The audits of the same day
(`~/Downloads/audit-briefs/links/`) found, on each archive's twelve longest pages, that Mazza links 11% of the names that resolve to one
dead person, Lerena 1.8% and Luwinski 3%, and that the archives that link at all do it with a helper an author has to type
(`<P n="..."/>`) or a browser script. One build-time tool fixes the part that is mechanical.

- `kit/tools/autolink.py` rewrites the **built** HTML in place: a name the archive's index lists becomes `<a href data-autolink>`.
- `kit/tools/checklinks.py` is the gate: it counts the names that are still unlinked, per page, and a page's count may only go down.
- `kit/tools/autolink_selftest.py` holds both to invented fixtures (`kit/data/autolink-fixtures/`) with a planted fault for every rule.

## Adopting it in an archive

1. **Generate the names index** from the archive's own people data, in the build, to a file such as `src/data/names-index.json`
   (it holds only names that already have public pages, so it may be committed or ignored):

   ```json
   {"people":    [{"name": "Given Family", "aliases": ["Family Given", "Given M. Family"], "url": "/people/given-family/"}],
    "ambiguous": [{"name": "Given Family", "url": "/people/?q=Given%20Family"}]}
   ```

   `people` = a name that resolves to exactly one **deceased** person who has a page. `ambiguous` = a name several people bear, sent to the
   archive's search or disambiguation address (`/people/?q=` or `/who/<slug>/`). Aliases are the archive's decision: the register-order form
   ("Family Given"), a spelling fold, a nickname plus surname. A name needs two words (`--min-words`, default 2); a bare given name is never
   linked. A name that appears twice with different addresses is skipped and counted, never guessed.
2. **Generate the living list** from the archive's living gate (the output of `living_rule.py`, not a second opinion): a JSON list of the
   names, aliases and `/people/<slug>/` addresses of every living or held-out person. It is a safety net (see below), so it must be
   authoritative. A living person's name never goes in a tracked file: write it to a file outside the repo (the way `checkprose.py`'s feed
   works) and pass it with `--living`. Where CI cannot have the names, pass the addresses only.
3. **Run `autolink.py` after the build**, before any step that reads the built HTML for its own purposes (the sitemap, a check that counts
   links or text, a search index made from pages). It is idempotent, so running it twice, or on a partial rebuild, is safe:

   ```
   python3 node_modules/@daviddef/archive-kit/kit/tools/autolink.py --dist dist --index src/data/names-index.json --living ../private/living.json
   ```

   It honours `ARCHIVE_OUT` like every kit tool (the environment wins over `--dist`).
4. **Run `checklinks.py` as a gate**, last, with the same `--index` and `--living`:

   ```
   python3 node_modules/@daviddef/archive-kit/kit/tools/checklinks.py --dist dist --index src/data/names-index.json --living ../private/living.json --floor .linkfloor.json
   ```

5. **Commit the floor.** The first time, run the same line with `--write-floor`: every page's current count becomes its ceiling. From then
   on a page may only go down; `--write-floor` after an improvement locks the gain in (and refuses to write while anything rose). Because
   `autolink.py` runs first, a healthy archive's counts are 0 and the floor is a column of zeros: any page that stops being linked, or any
   name that stops resolving to its link, shows up as a rise.

If the archive keeps a hand-typed helper (`<P n=...>`), nothing changes: a person already linked in a section by any link to the same
address counts as linked, and the tool adds nothing there.

## What the archive must guarantee

- **The index holds only deceased people with a page.** A living or held-out person is never in it, and neither is a name whose bearers
  include a living person: link such a name to the archive's disambiguation address or not at all. The tool cannot know who is living.
- **`--living` is the archive's authoritative living and held-out set**, built from the same decision as the pages, not by a person.
- **A unique name really is one person.** The tool matches strings, not meaning. If two different men are both "Given Family" the index
  must say so (`ambiguous`); the tool will otherwise link every mention to the one it was told.
- Every address is under a public prefix (`--allow-prefix`, repeatable, default `/people/` and `/who/`).
- The narrative text sits inside the scope element (default `<main>`; `--scope` names another tag).

## What the tool does and does not do

It links, in running text inside the scope: the **first** mention of a person in each section (a section runs from one `<h2>`/`<h3>` or
`<section>` boundary to the next; a page with none is one section), longest name first, then alias, whole words only.

| Case | Result |
|---|---|
| `Arena` inside `Arenaria`, `Arena-Rossi`, `d'Arena`, `Arenas`, `Arena1` | not linked (Unicode-aware word boundaries) |
| `Arena's`, `(Arena)`, `Arena.` | linked |
| `Hannah SANIGER`, `HANNAH SANIGER` for the name `Hannah Saniger` | linked, text left as written (a word in capitals matches; lower case does not) |
| `Zoe` + combining mark for `Zoë`, `&#8217;` or `'` for an apostrophe, `&nbsp;` for a space, a line break inside a name | matched |
| text inside `<a>`, `<h1>`-`<h6>`, `<nav>`, `<script>`, `<style>`, `<code>`, `<pre>`, `<title>`, `<svg>`, `<button>`, `<select>`, `<textarea>`, `<input>`, `<template>`, or any element with `data-no-autolink` (or under one) | never linked |
| text in an attribute, a comment, or outside the scope element | never linked |
| a person already linked in the section (any link to the same address, fragment ignored, even a later one) | not linked again |
| a name that overlaps a living name (`--living`) | not linked |
| a name written across two elements (`Given <b>Family</b>`) | not linked (one text node at a time) |
| a bare first name, an alias nobody listed, a surname alone, "he" | **not linked, by design** |
| names in a table the archive marks `data-no-autolink` (a register transcription that is not the same person) | not linked, by design |
| later mentions in a section after the first | plain text (one link per person per section keeps the page readable) |

Every other byte of the page is untouched: a tolerant tokenizer finds the text nodes, the tool inserts `<a href="..." data-autolink>` and
`</a>` around the matched characters, and writes the page back only if something changed (CRLF and the lack of a final newline survive).
The self-test removes the wrappers and requires the original bytes. `data-autolink` is the mark that lets the gate recognise, and a person
remove, what the tool added.

**Style.** The new anchor carries no scoped-style attribute (`data-astro-cid-...`). Global link styles apply to it; a page whose own
`<style>` restyles `a` for its component will not reach it. Style `a[data-autolink]` globally if that matters.

## The living rule, in code

The project's hardest rule is enforced three ways, and the tool prints only a **count**, never a name:

1. **A faulty index stops the run.** If any index entry's name, alias or address is also in `--living`, `autolink.py` and `checklinks.py`
   exit **2** before touching a page, and say only how many entries ("LIVING: 2 index entries are ones that the living list also holds").
2. **A living name is searched for in the text too.** If a living name overlaps a name the index lists ("Maria Rossi Bianchi" is living,
   "Maria Rossi" is dead), the dead name is left alone there.
3. **The gate fails any `data-autolink` link to a living address or carrying a living name,** and any `data-autolink` link whose address is not in
   the index or whose text is no longer a name of its address (a person merged, removed or hidden after the pass ran: rebuild and re-run).
   An index address outside the public prefixes is refused, exit 2.

## The gate

`checklinks.py` counts, per built page, the places where an indexed name is written in running text and the page has no link to that person
in that section: exactly the links `autolink.py` would still add. It prints counts only, and reports a page under a public prefix as a group
("3 page(s) under /people/") because that address is itself a name.

| Exit | Meaning |
|---|---|
| 0 | pass |
| 1 | fail: a page rose above its floor, a new page counts over `--new-page-max` (default 3), a stale link, a living link |
| 2 | refused: an empty build, no page with the scope element, an empty index, a living name in the index, an address outside the prefixes, an unreadable index, living list or floor |

A check that examined nothing has not passed: both tools refuse rather than print ok over an empty input.

## Known limits (state them, do not discover them)

- The first mention per section is linked; the count measures that, not the share of all mentions. An archive that wants every mention
  linked on a page must say so in a new option; none has asked.
- A name that is a real person on one page and a different person of the same name on another is the archive's `ambiguous` list to settle;
  the tool uses no page context.
- Names split across inline elements, and names in page titles, headings and tables the archive excludes, are not linked.
- The index is the archive's: a name it cannot resolve (a witness named only in an act) has no page, so no link.
