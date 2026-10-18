# The linking standard, v1

David, 18 October 2026, after looking at Mazza's `/scilla/` once the name-linking rollout had run: *"there are still loads of names with no
links ("Bruno", "Donato"...) and no links to records."* He was right, and `autolink.py` could not have fixed it. On `/scilla/` the people who
were left plain are people the archive **read from a register act** (parents, witnesses, officials): they have no person page, no `/who/`
entry and no line in the names index, so there is nothing for a linker to link to. Surname-first forms ("Donato Antonio") and a bare
"Bruno" in running prose can never be linked by matching strings. And every sentence that quotes a record (an act number, an ark, a film, a
volume) is plain text: no link to the record, no citation chip, and the scan itself sits in a gallery a hundred thousand characters away.
The audits of the same day (`~/Downloads/audit-briefs/links/`) found the same shape on all eight archives.

This is the standard every archive's narrative pages are held to, and the gate that holds them:

- `kit/docs/linking-standard.md` (this file): six numbered rules, each with what a tool enforces, what stays editorial, and the mark an
  author uses for a deliberate exception.
- `kit/tools/checkstandard.py`: reads the **built** site, the archive's names index and a small config the archive owns (`standard.json`),
  prints five counts per narrative page and a floor that may only go down.
- `kit/tools/checkstandard_selftest.py` with `kit/data/standard-fixtures/`: invented pages with a planted fault for every rule and a
  control for each; `--mutations` also breaks the tool, one way at a time, and requires the self-test to notice each.
- `kit/components/Rec.astro` with `kit/lib/rec.js`, `kit/data/rec-cases.json` and `kit/tools/rec_logic.mjs`: the record link, one tag per
  citation, that makes L3 and L4 cheap to meet (see "The `Rec` component" below).

It builds on `autolink.py` / `checklinks.py` (names that resolve; see `autolink.md`) and does not replace them: L1 *is* the checklinks count.

**Second round, 18 October 2026**, after the standard was measured on eight archives: scan keys and aliases are folded and a key that
matches nothing is counted (`--strict-config`); plates keyed from the archive's data (`scans.aliases_file`, `scans.manifest`);
`names.skip_quotes`; `names.allow` takes single words; `names.never_complete`; `scan_only` patterns; `allow_prefixes`; `tables`;
`record_links.markers`; and the `Rec` component. Every option is off unless the config names it: an existing config counts what it counted.

## Words used below

- **narrative page**: a hand-written page of research or story, as opposed to a generated list, table, register or index. The archive
  names its narrative pages in `standard.json` (`include`, `exclude`). A person's own page and `/who/` entries are never in scope.
- **section**: autolink's definition: the text between `<h2>`/`<h3>`/`<section>` boundaries inside `<main>`. A page with none is one section.
- **entry**: something a name can link to: a person page (`/people/<slug>/`), or a `/who/<slug>/` name entry (or the archive's equivalent
  prefix), listed in the names index. The index is the only list the tool believes.
- **passage**: one block of narrative prose that makes a statement: a `<p>`, `<li>`, `<dd>`, `<blockquote>`, or whatever other selector
  the archive's config names (`div.v` for a record-reading row, `figcaption`...).
- **record link**: a link to the record itself: one of the archive's own record entries (`/sources/`, `/documents/`, `/searched/`), its
  public record address on a host the config allows (an Antenati or FamilySearch ark, an NAA record), an in-page anchor to a plate on the
  same page, or a link an archive component marks `data-cite`. A link to another narrative page is **not** a record link.
- **held scan**: an image of the record that the archive holds and publishes, which its config can key to a citation (a plate named
  by volume, year and act number).

## The rules

| | The rule | Enforced by the tool | Stays editorial | An author's exception |
|---|---|---|---|---|
| **L1** | Every named deceased person who has an entry is **linked at the first mention in each section**. | `autolink.py` writes the link at build time; `checkstandard` counts what is still missing (it calls the same scan as `checklinks.py`, so the two cannot disagree). | Which names and aliases the index lists; which namesakes are `ambiguous`. | `data-no-autolink` on an element whose names are not claims (a transcription, a quotation). Nothing else. |
| **L2** | Every person the archive names from a record it has read **has an entry**, so a name quoted from a record is never a dead end. | Counts, per page, the distinct person-like phrases in bold or in the config's record-reading blocks that match **no** index entry (a name, an alias, a `/who/` entry). Fails any index address that is not a built page. | Making the entries (see "The second source of names"); judging that a phrase is a person; the living rule. | `names.allow` in the config (phrase + reason of 8+ characters), or `data-name-exempt="reason"` on the element. Both are counted (EX). |
| **L3** | Every **passage that quotes or relies on a record carries a link to that record**: in the same sentence by habit, and at least in the same passage or in the next block (a short source line or a figure), never at the foot of the page. | Counts passages that match one of the config's citation patterns with no record link in them, in an ancestor block, or in the next block (a short block, or a figure, in the same section). | That the link goes to the right record; that every record the passage relies on is covered by a pattern. | `data-cite-exempt="reason"` on the passage or an ancestor. Counted (EX). |
| **L4** | Where the archive **holds a scan its own rules let it show**, the scan or a thumbnail sits **in the same section** as the passage that cites it. Where it may not show it, the passage still links to the record (link-only). Never a living person's anything. | Counts passages whose citation keys to a held scan (an image on any built page, or the archive's own list) when no image with that key is in the same section. | Whether a scan may be shown (rights, terms); attribution and captions. The living rule (below). | The config's `scans.link_only` (pattern ids the archive may not show), or `data-cite-exempt="reason"`. |
| **L5** | Forms the machine cannot resolve (a **bare given name**, a **surname-first** form, a phrase like "the Donato line") are **written in full at their first mention in a section by the author, or tagged by the author**; they are never auto-guessed. | Counts a bare given name (a name the archive's index uses as a given name) with no full name containing it earlier in its section, and a capitalised name-like phrase in plain prose that matches no entry. | Writing the full name; deciding who "Bruno" is. The tag is an ordinary author link around the form (`<a href="/who/bruno-x/">Bruno</a>`) or the archive's own helper. | `data-name-exempt="reason"` on the element, or `names.allow`. Counted (EX). |
| **L6** | Each rule has a **ratchet**: a page's count may only go down; a new page may start with at most N (default 3) per rule; exemptions are counted and ratcheted too. | `.standardfloor.json`, written by `--write-floor`, which refuses while anything has risen. | Lowering the numbers; deciding N for a new page (`new_page_max` in the config; 0 is a fair choice for pages written after adoption). | None. A floor goes up only when a person edits the file, in a commit that says why. |

**The living rule is not relaxed by any of this.** An entry for a person read from a record follows the estate's living standard
(`PERSON-PAGE-SPEC.md`, `living_rule.py`): the index generator applies the archive's living gate; a person who is or may be living gets no
entry, no scan and no citation line of their own. `checkstandard` passes `--living` through to the same refusal `autolink.py` uses (an index
the living list also holds is exit 2, a count, no name), refuses an `allow` entry the living list holds, and fails a stale or living
`data-autolink` link on the pages in scope. It prints counts only.

## What each count means, exactly

**L1**, per page: the number of places `autolink.py` would still add a link. After `autolink.py` has run it is 0, and the floor is a column of
zeros. A page that stops being linked, or a name that stops resolving, is a rise.

**L2**, per page: the number of distinct phrases (compared with case, accents, hyphens and apostrophes folded) that are
- in running text inside `<strong>`/`<b>`, or inside any element matching `names.read_blocks` (the archive's record-reading rows),
- a run of 2 to 5 capitalised words (a lower-case particle such as *de*, *di*, *della*, *van* may join them), with function words
  (*The*, *Neither*, ...) trimmed off both ends, containing at least one word the archive's index uses as a given name,
- not inside a link, a heading, a table (unless `tables: "narrative"`), `<code>`, a quotation (with `names.skip_quotes`), or a `data-no-autolink` / `data-name-exempt` element,
- and equal to **no** name or alias in the index.

**L3**, per page: the number of passages that match a citation pattern, are not exempt, and have no record link in the passage, in an
enclosing block, or in the next block of the same section (the next block counts only when it is a figure or has at most
`next_block_max_chars` characters, 240 by default, so a long paragraph that happens to contain a link does not cover its neighbour).

**L4**, per page: the number of passages whose citation yields a scan key that is held but not shown in the passage's own section. The
key comes from named groups in the archive's patterns (`{y}-{n}` for year and act number), so two spellings of one citation ("Act 63 of
1888", "Matrimoni 1888, atto 63") reach one plate. A citation that yields no key (an act number with no year) is L3's business only.

**L5**, per page: the number of distinct (section, form) pairs, where a form is a bare given name nobody has written in full yet in that
section, or an unresolved name-like phrase outside L2's places. A name written in full once, or linked by the author, serves the rest of
its section.

**EX**, per page: the would-be violations that an exemption hides. Ratcheted, so an exemption cannot spread unseen.

## Adopting it in an archive

1. **Run `autolink.py` first** (see `autolink.md`) and keep `checklinks.py` as it is. `checkstandard` is a second gate, run last.
2. **Give the names index a second source** so a person read from a record has an entry: see "The second source of names". Until then L2 and
   L5 will count those people, honestly, and the floor holds the number.
3. **Write `standard.json`** at the archive's site root (below). The patterns are the archive's own: it knows how it writes "act 63 of 1888",
   what its arks look like, how its plates are named. False positives are tuned **here** (`not_names`, `stop_words`, `surname_words`, a more
   exact pattern), never by loosening the tool; false negatives are cured by adding a pattern.
4. **Mark the exceptions** the way the table says, each with a reason an editor would accept.
5. **Run the gate** after the build and `autolink.py`:

   ```
   python3 node_modules/@daviddef/archive-kit/kit/tools/checkstandard.py --dist dist --index .autolink/names-index.json \
       --config standard.json --living ../private/living.json --floor .standardfloor.json --strict-config
   ```

   It honours `ARCHIVE_OUT` like every kit tool. `--table` prints every page's five counts; `--new-page-max N` overrides the config.
   The entry prefixes the index may use (`/search/`, `/who/`...) belong in the config's `allow_prefixes`, so the CI call is just
   `--config`; `--allow-prefix` (repeatable) still works and the two are added together. `--strict-config` turns the configuration
   warning (a scan key or alias that matched nothing, below) into a failure: use it in CI.
6. **Commit the floor.** The first time run it with `--write-floor`: every page's counts become its ceiling. After that a page may only go
   down; `--write-floor` after an improvement locks the gain in and refuses to write while anything rose.
7. **Chip away.** Add an entry for a person (L2), link a citation (L3), move a plate into its section (L4), write a name in full (L5), run
   `--write-floor`. The number is the progress report.

### `standard.json`

```json
{
  "version": 1,
  "scope": "main",
  "include": ["/scilla/", "/crossings/"],
  "exclude": [],
  "new_page_max": 3,
  "allow_prefixes": ["/people/", "/who/", "/search/"],
  "tables": "records",
  "names": {
    "entry_prefixes": ["/people/", "/who/"],
    "read_blocks": [".rec"],
    "skip": ["table.register"],
    "skip_quotes": true,
    "skip_selectors": [".xlat"],
    "stop_words": ["Witnesses", "Act"],
    "given_names": [],
    "given_names_file": "given-names.json",
    "surname_words": [],
    "not_names": ["^(Santa|San) ", "\\b(Island|Street|Church)\\b"],
    "allow": [{"phrase": "A Name", "reason": "a notary named once in a deed; no page is planned"}],
    "never_complete": [{"name": "Given", "reason": "the subject of a page about a living person; the full name is not shown"}]
  },
  "citations": {
    "blocks": ["p", "li", "dd", "blockquote", "div.v"],
    "patterns": [
      {"id": "act", "flags": "i", "regex": "\\b(?:atto|act)\\s+(?P<n>\\d+)\\b(?:\\s+of\\s+(?P<y>\\d{4}))?", "key": "{y}-{n}"},
      {"id": "ark", "regex": "\\ban_ua\\d+"},
      {"id": "manifest", "flags": "i", "regex": "\\bmanifest\\b"}
    ],
    "record_links": {
      "prefixes": ["/sources/", "/documents/", "/searched/"],
      "hosts": ["antenati.cultura.gov.it", "familysearch.org"],
      "url_contains": [],
      "fragments": ["#plate-"],
      "markers": ["data-cite"]
    },
    "next_block_max_chars": 240
  },
  "scans": {
    "image_patterns": [{"regex": "/plates/scilla-(?P<t>matr|nati|morti)(?P<y>\\d{4})-atto(?P<n>\\d+)", "key": "{y}-{n}"}],
    "aliases": {},
    "aliases_file": null,
    "manifest": {"file": "plates.json", "id_field": "id", "key_field": "key"},
    "link_only": ["manifest"],
    "held_keys_file": null
  }
}
```

| Key | Meaning |
|---|---|
| `include` / `exclude` | Page addresses or `fnmatch` patterns (`/*`, `/places/*`). Required. Every `include` entry must match a built page, so a mistyped page cannot escape (exit 2). Pages under `entry_prefixes` are never in scope: their addresses are names. A page not in scope is not examined; `["/*"]` with an `exclude` list puts every new narrative page under the standard. |
| `names.read_blocks` | Selectors (`tag`, `.class`, `[attr]`, `[attr=value]`, combined) for the record-reading rows whose names L2 reads even without bold. |
| `names.skip` | Selectors where names are data, not narrative (a register table). Tables are skipped by default. |
| `names.stop_words`, `particles` | Words trimmed from the ends of a name-like run; words that may sit inside one. The tool has English and Italian defaults; the archive adds its own. |
| `names.given_names`, `given_names_file`, `surname_words` | The given-name vocabulary is the index's own given names (every word but the last of a name). Add names the index lacks (a register's), and mark a word that is a surname so it is never a bare given name. A word that ends three or more index names is taken for a surname (`auto_surname_min`). |
| `names.not_names` | Regular expressions for phrases that are not people ("Santa Maria", "Ellis Island"). This is where a false positive is cured. |
| `names.allow` | A phrase **or a single word** (a bare surname or given name) with a **reason of at least 8 characters**. Counted in EX (once per section for a bare name). A name the living list holds is refused (exit 2), whatever its length. |
| `names.never_complete` | Bare names (each with a reason of 8+ characters) that can never be written in full: the subject of a page about a living person, or of a one-person page whose every sentence is about them. Never counted in L2 or L5; counted in EX (once per section) and reported as one number, "N bare name mentions held by names.never_complete". An entry that is an index name is refused (exit 2): it would be linkable, so link it. A living subject's name is exactly what this is for, and it is not refused. |
| `names.skip_quotes` | `true` stops L2 and L5 reading names inside a quoted transcription: text between `«` and `»` (any `[open, close]` pairs in `names.quote_pairs`), `<q>`, `<blockquote>`, and elements matching `names.skip_selectors` (selectors: `.xlat`, `blockquote.cite`...). The names in a transcription are the document's, not the archive's claims. An unclosed mark ends with its block. `skip_selectors` and `quote_pairs` without `skip_quotes` are refused (they would do nothing). `data-no-autolink` still does the same for one element. |
| `tables` | (top level) How the gate treats table cells: `"narrative"` (names in cells are read, and each `td`/`th` is a passage), `"records"` (names in cells are data and skipped, each cell is a passage: a register row that cites an act must link it), `"skip"` (nothing in a table is read: no names, no passages, even if `citations.blocks` names `td`). Absent: the older behaviour (names skipped, cells passages only if `citations.blocks` names them). If `citations.blocks` names `tr`, `td` or `th` the gate does not add cells itself. `names.include_tables` is the older spelling of `"narrative"`; a contradiction is refused. A mode changes L3 and L5 a good deal (Booyzen and Lerena moved L3 by 100 to 146 on it), so it is the archive's decision, made once and written down. L1 is autolink's count and does not depend on it. |
| `allow_prefixes` | (top level) Address prefixes an index entry may live under (`/search/`, `/who/`...), added to any `--allow-prefix` given on the command line. Without either, the entry prefixes are used. |
| `citations.blocks` | Selectors for passages. Default `p, li, dd, blockquote`. |
| `citations.patterns` | `id`, `regex` (named groups allowed), `flags` (`i`), and optionally `key`, a template over the named groups (`{y}-{n}`) that names the scan this citation depends on, and `scan_only: true`. **A pattern with a `key` is a citation for L3 as well as a scan key for L4**; give it a locator inside the regex or it flags every sentence that mentions a town and a year. `scan_only` (requires a `key`) makes it a scan key and nothing else: a passage that matches only scan-only patterns is not a citing passage, owes no link, and is asked only for its scan. |
| `citations.record_links` | What counts as a link to a record: `prefixes` (root-relative), `hosts` (with subdomains) and optionally `url_contains` (e.g. `/ark:`), `fragments` (in-page `#plate-` anchors; the id must exist on the page), and `markers`: the attributes with which an archive's own component marks its record links (default `["data-cite"]`; the kit's `Rec` carries `data-cite`, an archive whose own component carries only `data-rec` adds it here). |
| `scans` | Required. Either `image_patterns` (regex over an `<img src>` with a `key` template over its groups; `aliases` fold spellings, `link_only` lists pattern ids the archive may not show, `held_keys_file` is a JSON list of keys the archive holds and the gate expects shown) or `{"none": "reason"}` for an archive with nothing to show. For plates whose file names carry no locator: `aliases_file` (a JSON object `{plate id: [keys]}` the archive generates) and/or `manifest` (`{"file": ..., "id_field": ..., "key_field": ...}`: a JSON list of plate objects, each with an id and a key or list of keys). A plate id is the file name with or without its extension. Paths are relative to the config. |

### Scan keys are folded, and a key that matches nothing is counted

A key is a string such as `1888-63`. The gate **folds** every key the way it folds text (case and accents folded, apostrophes
removed, every run of punctuation and spaces one space), on both sides and including the literal text of a template, an alias, a
held-keys list, an aliases file and a manifest, so `Orchard-Deed`, `orchard deed` and a plate named `orchard-deed.jpg` meet. Before
this, an unfolded literal key silently never matched and L4 read 0 for the wrong reason (Falco and Lerena both hit it).

What cannot meet is counted. After the run the gate prints, as a count and never a key,

```
checkstandard: warning: N configured scan keys matched no citing passage and no held plate
```

for each alias no citation or image gave a value for, each literal pattern key whose pattern hit no passage and whose plate is held
nowhere, and each plate id in the aliases file or manifest that no image carries and no citation reaches. It is a warning; with
`--strict-config` it is a failure (exit 1, and `--write-floor` refuses). An archive that has scans configured and sees L4 at 0
should look at this line before it believes the 0.

### Marking an exception

```html
<p data-cite-exempt="the sentence restates the one above, which carries the link">...</p>   <!-- L3, L4 -->
<p data-name-exempt="the deed spells only this name">... <span data-name-exempt="...">Bruno</span> ...</p>   <!-- L2, L5 -->
<div data-no-autolink> ... a transcription ... </div>                                                      <!-- L1 (and L2, L5) -->
```

An exemption with no reason (an empty or blank attribute) is a failure, whatever the floor says. Each one with a reason raises EX, and
EX may not rise. For a name that can never be completed, `names.never_complete` says so once for the whole archive instead of an
attribute on every element.

## The second source of names (what makes L2 passable)

`autolink.py` reads an index built from the archive's people data. A person the archive has only **read from a record** (a parent, a witness, a
sindaco, a godparent) is in a data file, not in that index, so no name page exists for the linker to find. L2 is passed by giving that
person an entry the index lists: a `/who/<slug>/` name page that says who the name is, where the archive read it (the act, with a record
link, and the scan where it may be shown), and which pages mention it. The index generator takes **two sources**: the people data (as now)
and a list of persons read from records. Entries from the second source are `people` rows with a `/who/` address, or `ambiguous` rows when
the same name was read in several acts without proof that it is one person; aliases include the register-order form ("Family Given"). The
same living rule applies to both. This is the archive's work; the kit's proposal is in the report that accompanied this standard.

## What the heuristics cannot catch (so nobody trusts them further than they go)

- A person-like phrase is judged by capitalisation and by the archive's own given names. A name made only of words the index has never seen as a
  given name is invisible to L2 and L5 until the archive lists its given names (`given_names_file`, built from the register data).
- A name split across two elements ("Given <em>Family</em>"), a name in a heading or a table, and a name written in lower case are not seen.
- A bare surname ("the Donato line") is never counted: it is a family reference as often as a person, so only the author can say.
- A false match is possible both ways: a place or an office that looks like a name (cure it with `not_names`), a saint, a double given name
  that reads as a surname-first form.
- L3 and L4 find only the citations the config's patterns match. A passage that relies on a record without quoting a locator is invisible.
  A citation that gives an act number but no year yields no scan key, so L4 does not see it.
- L3 accepts a record link anywhere in the passage, not only in the sentence; the sentence rule is the author's. An outgoing link is a record
  link if its host is allowed; the gate cannot tell whether it is the right record.
- L4 treats any image whose file name matches the key as the scan; it does not look at the image.
- None of this proves a statement is true. It proves a reader can see where it came from and where to go.

## Exit codes

| Exit | Meaning |
|---|---|
| 0 | pass |
| 1 | fail: a rise, a new page over the maximum, an index address that is not a built page, a stale or living `data-autolink` link, an exemption without a reason, and under `--strict-config` a scan key or alias that matched nothing |
| 2 | refused: no built page, no page in scope, an `include` entry that matches nothing, an unreadable, empty or invalid config (an unreadable aliases file or manifest, a `never_complete` entry that is an index name, `skip_selectors` without `skip_quotes`...), a floor that is not valid, a living conflict, and a run in which no passage matches a citation pattern (nothing was examined) |

A check that examined nothing has not passed.

## The `Rec` component (L3 and L4 in one tag)

`kit/components/Rec.astro` renders the record link of a citation the author has already written, from the archive's records table:

```astro
---
import Rec from "@daviddef/archive-kit/components/Rec.astro";
import records from "../data/records.json";
---
<p>The groom was of age. The act is <Rec records={records} act="63/1888">act 63 of 1888</Rec>.</p>
<Rec records={records} id="marriage-1888-63" thumb>act 63 of 1888</Rec>     <!-- a figure: between paragraphs, not inside one -->
```

An archive that uses it often wraps it once (`src/components/Rec.astro` imports the table and passes it on).

**The records table** (JSON, an array of rows or `{"records": [...]}`; the archive generates it from the data it already holds):

| Field | Meaning |
|---|---|
| `id` | Unique. What `<Rec id="...">` names, and what the link carries in `data-rec`. |
| `url` | Where the record is: `https://...`, `http://...`, or a root-relative address of the archive's own. Nothing else is accepted (no `javascript:`, `data:`, `//host`, relative address). Required unless the row is flagged `living` or `hold`. |
| `label` | A short human name. The tooltip, the figure's alt text, and the link text when the author wrote none. |
| `kind` | Optional: `act`, `ark`, `census`... Carried as `data-kind`. |
| `key` | Optional: the locator an author may cite it by (`"63/1888"`), a string or a list. Compared folded, so `63/1888`, `63-1888` and `63 / 1888` are one key; two records may not share one. `<Rec act="...">` looks a row up by it. |
| `plate` | Optional: the scan the archive holds, a plain file name or path under the plates base (no `..`). |
| `show` | `true` where the archive's own rules let it show that scan. Exactly `true`; any other value means "do not show". |
| `living`, `hold` | `true` for a record about a person who is or may be living (`living`) or one the archive withholds for any other reason (`hold`). Any value but an unmistakable "no" counts. A flagged row is **never drawn**: no link, no figure, no text, and its plate is never read. The archive's own living gate decides what to flag; `Rec` only honours the flag. |
| `w`, `h` | Optional: the plate's pixel size, to stop the page jumping. |

**What it draws.**

- A link (the class is `lk-rec`, namespaced because archives already own a `.rec` class of their own: Falco's is a grid and Luwinski's was a bare rule): `<a class="lk-rec" href data-rec="<id>" data-cite data-kind title [rel="noopener"]>the author's words</a>`. With no words, the label.
- With the `thumb` prop, and only when the row has a `plate` and `show` is `true`: `<figure class="rec-fig" id="plate-<name>">` holding the
  scan's thumbnail (linked to the full file) and a caption that carries the link. Otherwise the link alone (link-only). The first figure
  of a plate on a page takes the `id`, so `#plate-...` fragments resolve; a second keeps its figure and gives up the `id`.
- Nothing, for a flagged row. An id or locator the table does not hold **stops the build**; `soft` draws the author's words unlinked.
- Everything the author or the table supplies is escaped; addresses are checked as above. `plateBase` (default `/plates/`) says where plates live.

**How the gate recognises it.** The link carries `data-cite`, the mark `checkstandard` has always counted as a record link, so no host or
prefix has to be configured for the records it points to (an L3 satisfied by the component, not by a lucky URL). The figure's caption link
covers the passage before it (the next block, a figure), and its image, named by the plate, is the scan L4 asks for: configure the plate
names in `scans.image_patterns` (or key them with `scans.manifest` / `scans.aliases_file`). An archive whose own component marks links
only with `data-rec` adds `"markers": ["data-cite", "data-rec"]` to `citations.record_links`. `Rec` is the writing half; the gate is
unchanged by it and remains the check that every citing passage does carry one.

Adopting: (1) generate the records table from the data the archive already holds; (2) wrap each citation the gate counts in L3 in a
`<Rec>`, passage by passage, running the gate to watch the number fall; (3) add `thumb` where a plate is held and may be shown and the
passage's section has none; (4) keep the table's `living` and `hold` flags generated from the archive's living gate, never typed by hand.
The logic is tested without Astro in `kit/tools/rec_logic.mjs` (shared cases in `kit/data/rec-cases.json`, planted faults, and a run of
the gate over the markup it draws).

## Still proposed, not built

- A names-index generator that takes persons read from records as a second source, as above.
