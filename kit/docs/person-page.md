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
| `components/PersonSection.astro` | one section with its fixed heading and anchor |
| `components/EvidenceChip.astro` | a grade (the kit's `Evidence`) and a source, side by side; no grade beside an index entry or an image held |
| `styles/personpage.css` | new classes only; `persontree.css` is untouched |
| `tools/checkperson.py` | reads the **built** pages and fails (advisory unless `--strict` or `--max`; refuses an empty build) |
| `tools/checkperson_selftest.py` | plants one fault per rule (values 1799, "Testville"); the checker must name it |
| `tools/checkperson_logic.mjs` | the library's cases, **including the shared living-rule cases**, and planted faults in a copy of `person.js` |

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
```

Exit 0 is a pass or an advisory run; 1 is a FAIL under `--strict`/`--max`; **2 is "could not see a people page", which is not a pass**: no directory, an empty one, one that holds only redirect pages, or fewer than `--min-pages` (at least 1). It reads pages built with `PersonPage` against the whole spec (section order, headings, anchors) and every other person page against what can be said of any people page (one `h1` with no long qualifier, a chart or the reason for none, a named person has a page, dates, grade words, images, and everything about a living person). "Living" is what the page declares or what `--living-urls` says (computed by the archive from `living_rule.py`); `noindex` alone does not make a page living.

## Not done, on purpose

A row in `shared-pages.json` (it would change what `checkshared.py` reports everywhere), regenerating `docs/components.md`, a `check:people` script in any archive, and any repin. A new kit commit means each archive repins `package.json` and `package-lock.json` together (`checkpin.py`); push one archive and watch it deploy before the rest.
