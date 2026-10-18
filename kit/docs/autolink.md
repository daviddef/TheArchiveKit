# Autolink: every name that resolves is linked, and the number cannot get worse

David, 18 October 2026: *"why do so many names on our narrative pages have no link to their person page?"* The audits of the same day
(`~/Downloads/audit-briefs/links/`) found, on each archive's twelve longest pages, that Mazza links 11% of the names that resolve to one
dead person, Lerena 1.8% and Luwinski 3%, and that the archives that link at all do it with a helper an author has to type
(`<P n="..."/>`) or a browser script. One build-time tool fixes the part that is mechanical.

- `kit/tools/autolink.py` rewrites the **built** HTML in place: a name the archive's index lists becomes `<a href data-autolink="...">`
  (the value says how it was decided: `person`, `near` or `search`; see "Shared names" below).
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
   linked. A name that appears twice with different addresses is skipped and counted, never guessed. Two optional fields are described under
   "Shared names": `resolve` on an `ambiguous` entry, and a top-level `labels`.
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

## Shared names: from the search list to the person, where the data decides

A name several people bear used to link to the archive's filtered people list wherever it stood, because the tool uses no context. That sent a
reader who clicked "María Lerena" in the card of her husband to a list of 18 people, not to her page. The tool now links every mention
of a shared name in one of three ways, written into the link as `data-autolink`:

| `data-autolink` | Meaning | Where it goes |
|---|---|---|
| `person` | the name resolves to one deceased person (the index's `people`) | that person's page |
| `near` | a shared name, decided by the people named in its own section | the one bearer the archive's relationship data points to |
| `search` | a shared name the data could not decide | the archive's search address, marked so the reader is not misled |

**`resolve` rules (the archive generates them from relationship data).** An `ambiguous` entry may carry

```json
{"name": "Given Family", "url": "/people/?q=Given%20Family",
 "bearers": ["/people/first-bearer/", "/people/second-bearer/"],
 "resolve": [{"near": "/people/spouse-of-first/", "url": "/people/first-bearer/"},
             {"near": "/people/child-of-second/", "url": "/people/second-bearer/"}]}
```

`bearers` lists the deceased bearers of the name who have a page and are **not** in `people` (a name that several people bear is not in `people`,
so without it a bearer could never be a rule's `url`); a rule's `url` must be in `people` or in the same entry's `bearers`, and its `near` in `people`.
A rule reads: *a relative of exactly one bearer of this name, `near`, is named in the same section, so the name there is that bearer, `url`*.
For each mention of the ambiguous name the tool takes the people **named beside it**: in the same section (the tool's existing section, from one
`<h2>`/`<h3>`/`<section>` to the next), in the same **block** (the innermost `<p>`, `<li>`, `<tr>`, `<dd>`/`<dt>`, `<blockquote>`, `<figcaption>`,
`<caption>` or `<summary>` around it; text with no such element around it is one block per section), and within the **near window**: 120
characters of text either side of the shared name by default (markup does not count). A person is named by a plain mention of an indexed
single-bearer person, or by any link to the person's page (a hand-made one, or an autolink from this run). The window is the index's top-level
`"nearWindow": N` (or `--near-window N` on the tools, which must agree; `0` = anywhere in the block). The block and the window exist because a
section on a long page is not one place. Lerena's trial, run first with the whole section, linked "Luis" in a list of 1895 births to the wrong Luis
because his cousin was named three screens up, and "Carmen (d. 1841, aged three)" in a register table to a different Carmen because the row above
held a relative of that one; with the block and 120 characters, 75 of the 95 decisions stood within 35 characters of their relative and none beyond 118.
The card that started this ("named by their son...", Juan Carlos and María in one paragraph) is one block. Then:

- exactly one distinct `url` is decided: the mention is linked to it, `data-autolink="near"` (and once per section like any person: a bearer already
  linked in the section covers the mention);
- no rule fires: the search link, `data-autolink="search"`;
- two rules fire for **different** `url`s in one section (the names of two relatives, or a relative of both bearers): the search link. The tool never
  picks one;
- a **counter-rule** `{"near": R, "url": null}` fires for a bearer who cannot be linked: the archive writes it for a relative R of exactly one
  bearer who is living, held out or has no page. Named in the section it keeps the tool from choosing another bearer (`fired` then holds `null` and
  a person: search link), and alone it decides nothing. If the index is committed, remember that a counter-rule says "a relative of this unlinkable bearer is
  R": it names nobody, but an archive that holds even that back leaves counter-rules out and accepts a bit less safety, or keeps the index outside the repository.

A relative outside the block or the window, inside a block marked `data-no-autolink`, in a heading, or in another section, names nobody for this purpose (a link to the relative's
page in the section does count). A `near` link is a result of a rule and never evidence for another: it names nobody (otherwise one decision could
change another's on the next run, and the gate would fail a link the tool had just made).

**How an archive generates the rules.** For each shared name N, let its bearers B1..Bk be everyone the pages might mean by it (living and held-out
people included: they count when deciding *exactly one*, though they are never a `url`). For each bearer B and each **spouse** S of B (and, where the
data has no spouse edge, the other recorded parent of a child of B, who counts as a spouse) that is a **single-bearer indexed person** (an entry in
`people`), add `{"near": S.url, "url": B.url}` **only when S is related to exactly ONE bearer of N, by any kind of relationship the data holds**
(spouse, parent, child, sibling, co-parent, either direction). If S is also related to a second bearer, write no rule for S. When the one bearer cannot
be linked (living, held out, no page) write `{"near": S.url, "url": null}` (a counter-rule, below) or nothing. Never derive a rule from a surname, a
place, a date or a name resemblance.

*Why spouses, and not parents or children.* Names run down families: a father and his son often share a name, and the parent of the son is also the
spouse (or parent) of the namesake father. A text that names "Luis Lerena" beside Julia Juanicó means the husband, but a rule built on the son's
mother points at the son. In Lerena's trial the same recipe run on spouse and co-parent relationships alone made 95 decisions, and a reading of all 95
in their sentences found none wrong. Run on parent, child and sibling relationships as well it made 134, and the 39 it added held about ten wrong ones
(a groom, a godfather, and a father, each taken for the namesake son; a woman taken for her granddaughter). The tool accepts any rule, so the
generator is where this is decided: use spouse and co-parent rules, and add parents, children or siblings only for a name that no one in the data
inherited from a parent.

*The rule is only as good as the relationship data*, so count a relationship in every form the data holds it: an inverse edge (A lists B as a child:
B is related to A), two people who are the recorded parents of one child (related), and a relative written inside a bearer's own register name
("Alejandro LERENA (m. Margarita Fernandez Alvarez)": a wife the data holds only there). A relative whose tie to a second bearer the data only implies
would otherwise look exclusive to the first, and the rule would point at the wrong man. (Found in Lerena's trial: a mother recorded only on her
children looked related to the son, and not to the father who shared his name.) A relative named in a bearer's *note* is not a relationship; do not
make a rule from one, though it is reasonable to refuse a rule when a second bearer's note names the same relative.

The tool checks what it can: a rule whose `near` is not in `people`, whose `url` is in neither `people` nor the entry's `bearers`, that is under no
public prefix, is living, or points at itself stops the run (exit 2), and so does a living address in `bearers`. A relative who leads to two bearers
decides nothing (two rules disagree: the search link) and the run's summary counts them. The tool cannot check that a relationship is true or complete,
or that the text names the namesake it means; a decision the data supports but the sentence contradicts ("another Don Luis Lerena", "the elder")
is the residual risk, and the reason the window is short and the generator uses the strongest relationship.

**The cue on an unresolved link.** A `search` link is written

```html
<a href="/people/?q=Given%20Family" data-autolink="search" class="lk-shared"
   title="Several people share this name: opens the list"
   aria-label="Given Family, several people share this name: opens the list">Given Family</a>
```

The text can be changed with a top-level `"labels": {"shared": "..."}` in the index (an empty string drops the title and the aria-label and keeps the
class). The kit ships no style for `.lk-shared`, so by default nothing looks different; an archive that wants the cue visible adds, in its global CSS,

```css
a.lk-shared { text-decoration-style: dotted; }   /* the link opens a list, not a person */
```

**Order of the index fields an archive must generate:** `people[{name, aliases?, url}]`, `ambiguous[{name, aliases?, url, resolve?: [{near, url}]}]`,
`ambiguous[].bearers?: [url]`, and optionally `labels: {shared}` and `nearWindow`. Nothing else is read.

## What the archive must guarantee

- **The index holds only deceased people with a page.** A living or held-out person is never in it, and neither is a name whose bearers
  include a living person: link such a name to the archive's disambiguation address or not at all. The tool cannot know who is living.
- **`--living` is the archive's authoritative living and held-out set**, built from the same decision as the pages, not by a person.
- **A `resolve` rule is true.** `near` is a recorded relative of `url`'s person and of no other bearer of that name. The tool checks only that both
  addresses are indexed people and not living; it cannot know the relationship.
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
3. **The gate fails any `data-autolink` link to a living address or carrying a living name** (a `near` link included: it goes to a rule's `url`,
   which must be an indexed deceased person, and the run stops if a rule names a living address), and any `data-autolink` link whose address is
   not in the index or whose text is no longer a name of its address (a person merged, removed or hidden after the pass ran: rebuild and re-run).
   An index address outside the public prefixes is refused, exit 2.

## The gate

`checklinks.py` counts, per built page, the places where an indexed name is written in running text and the page has no link to that person
in that section: exactly the links `autolink.py` would still add. It prints counts only, and reports a page under a public prefix as a group
("3 page(s) under /people/") because that address is itself a name.

| Exit | Meaning |
|---|---|
| 0 | pass (it prints how many links are `exact`, `near` and `search`) |
| 1 | fail: a page rose above its floor, a new page counts over `--new-page-max` (default 3), a stale link, a living link, a `near` link that its rules do not decide in its own section (the relative is gone, the address or name is not in the index, two rules disagree), a `search` link without the class `lk-shared` or the label |
| 2 | refused: an empty build, no page with the scope element, an empty index, a living name in the index, an address outside the prefixes, an unreadable index, living list or floor |

A check that examined nothing has not passed: both tools refuse rather than print ok over an empty input.

## Known limits (state them, do not discover them)

- The first mention per section is linked; the count measures that, not the share of all mentions. An archive that wants every mention
  linked on a page must say so in a new option; none has asked.
- A name that is a real person on one page and a different person of the same name on another is the archive's `ambiguous` list to settle;
  the only context the tool uses is the `resolve` rules and the people named in the same section. A shared name with no relative beside it stays
  a (marked) search link.
- Names split across inline elements, and names in page titles, headings and tables the archive excludes, are not linked.
- The index is the archive's: a name it cannot resolve (a witness named only in an act) has no page, so no link.
