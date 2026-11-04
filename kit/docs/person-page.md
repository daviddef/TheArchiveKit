# The people page — short README

The reasoning, the measurements and the four rulings (16 October 2026) are in [PERSON-PAGE-SPEC.md](PERSON-PAGE-SPEC.md); the living-people standard it implements is section 8 of that spec. This file is how to use what is on the branch.

**Apart from one added function in `living_rule.py`, nothing here changes an existing kit file, and nothing is wired into any archive.** An archive adopts it a step at a time; each step is small and `checkperson.py` says how far along it is.

## What is here

| | |
|---|---|
| `lib/person.js` | the decisions as pure functions: the six sections, the five grades and seven source words, dates, **the living rule (the JavaScript twin of `living_rule.py`)**, names, stubs, structured data |
| `data/living-rule-cases.json` | the one list of cases both implementations are tested against |
| `components/PersonPage.astro` | the page, in the spec's order; a living person is name, relationships, town and country and nothing else; throws on a held-out person |
| `components/PersonChart.astro` | an adapter over the kit's `PersonTree`: one set of source words, dates from fields, living relatives by name only, an empty chart that says why |
| `lib/personstory.js`, `lib/personevidence.js` | story mode: the pure logic of a life told on a timeline (spec section 2a), with the kit's living rule |
| `components/PersonStory.astro`, `PersonGlance`, `PersonLore`, `PersonEvidence`, `PersonEvTag`, `PersonWorldAround`, `PersonRootsViews` | the inside of the story-mode sections; pass them in the `story`, `glance`, `lore`, `sources`, `world` and `where` slots of `PersonPage` (the `story` slot puts the page in story mode) |
| `components/PersonSection.astro` | one section with its fixed heading and anchor |
| `components/EvidenceChip.astro` | a grade (the kit's `Evidence`) and a source, side by side; no grade beside an index entry or an image held |
| `styles/personpage.css` | new classes only; `persontree.css` is untouched |
| `tools/checkperson.py` | reads the **built** pages and fails (advisory unless `--strict` or `--max`; refuses an empty build) |
| `tools/checkperson_selftest.py` | plants one fault per rule (values 1799, "Testville"); the checker must name it |
| `tools/checkperson_logic.mjs` | the library's cases, **including the shared living-rule cases**, and planted faults in a copy of `person.js` |
| `tools/checknamepages.py` | reads the **built** name pages (`/who/<name>/`) and fails when a page's «N people of the name» differs from the person pages of that name in the build, or when it does not link one of them (see below) |
| `tools/checknamepages_selftest.py` | plants a wrong count, an unlinked person page, a silent name page and a living person; run as `checknamepages.py --selftest` |

## Using it

```astro
---
import Base from "../../layouts/Base.astro";
import PersonPage from "@daviddef/archive-kit/components/PersonPage.astro";
import PS from "@daviddef/archive-kit/data/public-sources.json";
import { personMeta } from "@daviddef/archive-kit/lib/person.js";
import "@daviddef/archive-kit/styles/persontree.css";
import "@daviddef/archive-kit/styles/personpage.css";

const m = personMeta(person, { siteName: "The Falco Archive", sources: PS });
---
<Base title={m.title} dek={m.description} noindex={m.noindex} about={m.about}>
  <PersonPage person={person} nameHref={nameHref} peopleHref="/people/">
    <Fragment slot="record">…</Fragment>
    <Fragment slot="sources">…</Fragment>
  </PersonPage>
</Base>
```

`person` carries `id`, `name`, `born`, `died`, `buried`, `dead` (an undated death), `citations`, `town` and `country` (for a living person), and `relations: { parents, spouses, children, siblings }`, where a relation is `{ id, name, href, born?, died?, buried?, dead?, citations?, parentLiving?, source?, line?, ambiguous? }`. **Who is living is computed** from those (born 80 years ago or less by year, no death or burial recorded, no public record source); a hand-set `living` or `presumedLiving` is not read. `source` takes **any archive's own word** (`register`, `read`, `doc`, `index`, `tree`, `lore`, `inf`…); a word nobody recognises is drawn as *unmarked*, with the word quoted, never as a kind default. The `Base` must forward `about` to `JsonLd.astro` (seven already do), and **must not build a person who is held out** (an undated person with a living parent, or promised privacy by id): `PersonPage` throws on one.

Stepwise: (1) swap the archive's `PersonTree.astro` wrapper for `PersonChart`; (2) wrap existing sections in `PersonSection`; (3) move the page under `PersonPage`; (4) turn the checker on.

## The checks

```
python3 kit/tools/checkperson.py --dist dist --people /people/                 # advisory: counts, exits 0
python3 kit/tools/checkperson.py --dist dist --people /person/ --strict         # exit 1 on any FAIL
python3 kit/tools/checkperson.py --dist dist --max 40                           # ratchet: fail only if FAILs rise above 40
python3 kit/tools/checkperson.py --dist dist --living-urls living.txt --sitemap dist/sitemap.xml --require-jsonld
python3 kit/tools/checkperson_selftest.py                                       # prove it can still fail
node kit/tools/checkperson_logic.mjs                                            # the library, and the shared living-rule cases
python3 kit/tools/living_rule_selftest.py                                       # the same shared cases against living_rule.py
python3 kit/tools/checknamepages.py --dist dist                                  # name pages against person pages: exit 1 on a finding
python3 kit/tools/checknamepages.py --selftest                                  # prove it can still fail
```

### The name-page check (`checknamepages.py`)

A name page says how many people carry a name; the number is written by the archive, from a list, and drifts from the pages.
On 5 November 2026 `/who/ivan-defranceski/` said «3 people of the name» with five person pages in the build, and Booyzen's
`/who/george-mountjoy/` said 2 with three pages and linked one. The check reads the build and fails on two things:

- **count**: the name page claims N and the build holds M person pages (`data-person-page`) of that name. A person page belongs to
  the name when its h1, accents and case folded, is the name, or the name plus a parenthesised qualifier, or the name plus « of …».
- **unlinked**: the name page does not link to a person page of its name. This is checked on every name page, also on one that
  claims no number (that is only a note).

A living person's page is counted and never named in a message (a slug can carry a birth year). Exit 0 clean, 1 findings, 2 it could
not see a name page or a person page (an empty build is not a pass). `--max N` is a ratchet for an archive that starts with findings;
`--advisory` reports and exits 0. A new wording of the claim is one line in `CLAIMS` at the top of the tool.

To add it to an archive's CI, after the build and next to its other checks:

```
python3 node_modules/@daviddef/archive-kit/kit/tools/checknamepages.py --dist "${ARCHIVE_OUT:-dist}" --who-prefix /who/ --person-prefix /people/ --max <today's count>
```

Start with `--max` at the count it reports today, and lower it as the name pages are fixed; remove `--max` when it reaches 0.

Exit 0 is a pass or an advisory run; 1 is a FAIL under `--strict`/`--max`; **2 is "could not see a people page", which is not a pass**: no directory, an empty one, one that holds only redirect pages, or fewer than `--min-pages` (at least 1). It reads pages built with `PersonPage` against the whole spec (section order, headings, anchors) and every other person page against what can be said of any people page (one `h1` with no long qualifier, a chart or the reason for none, a named person has a page, dates, grade words, images, and everything about a living person). "Living" is what the page declares or what `--living-urls` says (computed by the archive from `living_rule.py`); `noindex` alone does not make a page living.

## Not done, on purpose

A row in `shared-pages.json` (it would change what `checkshared.py` reports everywhere), regenerating `docs/components.md`, a `check:people` script in any archive, and any repin. A new kit commit means each archive repins `package.json` and `package-lock.json` together (`checkpin.py`); push one archive and watch it deploy before the rest.
