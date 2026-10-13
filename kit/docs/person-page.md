# The people page — short README

A proposal, not a ruling. The reasoning, the measurements and the four decisions that are the owner's are in [PERSON-PAGE-SPEC.md](PERSON-PAGE-SPEC.md). This file is how to use what is on the branch.

**Nothing here changes an existing kit file, and nothing is wired into any archive.** An archive adopts it a step at a time; each step is small and `checkperson.py` says how far along it is.

## What is here

| | |
|---|---|
| `lib/person.js` | the decisions as pure functions: the six sections, source words, dates, the living rule, names, stubs, structured data |
| `components/PersonPage.astro` | the page, in the spec's order; refuses to render a living person's record |
| `components/PersonChart.astro` | an adapter over the kit's `PersonTree`: one set of source words, dates from fields, an empty chart that says why |
| `components/PersonSection.astro` | one section with its fixed heading and anchor |
| `components/EvidenceChip.astro` | a grade (the kit's `Evidence`) and a source, side by side |
| `styles/personpage.css` | new classes only; `persontree.css` is untouched |
| `tools/checkperson.py` | reads the **built** pages and fails (advisory unless `--strict` or `--max`) |
| `tools/checkperson_selftest.py` | plants one fault per rule; the checker must name it |
| `tools/checkperson_logic.mjs` | 71 cases against `lib/person.js`; no build, node only |

## Using it

```astro
---
import Base from "../../layouts/Base.astro";
import PersonPage from "@daviddef/archive-kit/components/PersonPage.astro";
import { personMeta } from "@daviddef/archive-kit/lib/person.js";
import "@daviddef/archive-kit/styles/persontree.css";
import "@daviddef/archive-kit/styles/personpage.css";

const m = personMeta(person, { siteName: "The Falco Archive" });
---
<Base title={m.title} dek={m.description} noindex={m.noindex} about={m.about}>
  <PersonPage person={person} nameHref={nameHref} peopleHref="/people/">
    <Fragment slot="record">…</Fragment>
    <Fragment slot="sources">…</Fragment>
  </PersonPage>
</Base>
```

`person` carries `name`, `born`, `died`, `living`, `relations: { parents, spouses, children, siblings }`, where a relation is `{ name, href?, born?, died?, source?, line?, ambiguous?, living?, gap? }`. `source` takes **any archive's own word** (`register`, `read`, `doc`, `index`, `tree`, `lore`, `inf`…); a word nobody recognises is drawn as *unmarked*, with the word quoted, never as a kind default. The `Base` must forward `about` to `JsonLd.astro` (seven already do).

Stepwise: (1) swap the archive's `PersonTree.astro` wrapper for `PersonChart`; (2) wrap existing sections in `PersonSection`; (3) move the page under `PersonPage`; (4) turn the checker on.

## The checks

```
python3 kit/tools/checkperson.py --dist dist --people /people/                 # advisory: counts, exits 0
python3 kit/tools/checkperson.py --dist dist --people /person/ --strict         # exit 1 on any FAIL
python3 kit/tools/checkperson.py --dist dist --max 40                           # ratchet: fail only if FAILs rise above 40
python3 kit/tools/checkperson.py --dist dist --living-urls living.txt --sitemap dist/sitemap.xml --require-jsonld
python3 kit/tools/checkperson_selftest.py                                       # prove it can still fail
node kit/tools/checkperson_logic.mjs                                            # the library's 71 cases
```

Exit 0 is a pass or an advisory run; 1 is a FAIL under `--strict`/`--max`; **2 is "could not see a people page"**, which is not a pass. It reads pages built with `PersonPage` against the whole spec (section order, headings, anchors) and every other person page against what can be said of any people page (one `h1`, a chart or the reason for none, dates, grade words, images, and everything about a living person). "Living" is what the page declares or what `--living-urls` says; `noindex` alone does not make a page living.

## Not done, on purpose

A row in `shared-pages.json` (it would change what `checkshared.py` reports everywhere), regenerating `docs/components.md`, a `check:people` script in any archive, and any repin. A new kit commit means each archive repins `package.json` and `package-lock.json` together (`checkpin.py`); push one archive and watch it deploy before the rest.
