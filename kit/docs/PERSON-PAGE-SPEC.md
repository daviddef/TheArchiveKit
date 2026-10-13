# The people page — a proposed canonical page

**Status: a proposal. Nothing in it is decided.** Four decisions are the owner's (section 13); each has options, trade-offs and a recommendation, and none of them is treated as settled anywhere in the code on this branch. Everything else here is a default chosen so that the component can be built; it is a parameter, not a ruling.

Written 13 October 2026 against the eight archives' *built* pages (Defranceschi, Falco, Blažević, Lerena, D'Arcy, Mazza, Booyzen, Luwinski). The sites' live addresses could not be reached from the environment this was written in, so every number below comes from building each archive from its repository at the kit commit it pins and reading the HTML. Read "measured" as "measured on that build".

## 1. What the measurement changed in the brief

The comparison this started from was 16 sampled pages per archive. At full scale (every person page) some of it holds and some does not.

| The hypothesis | At full scale |
|---|---|
| Six archives carry their own forked `PersonTree.astro` (115–171 lines) | **Wrong, and it changes the plan.** All six import the kit's `PersonTree.astro` and `persontree.css` and draw nothing themselves (Falco 150 lines, Blažević 126, Lerena 156, D'Arcy 135, Mazza 171, Booyzen 115). They are *adapters*. What they adapt is what drifted: source words, date strings, living relatives, the reason a chart is empty. The one real fork of the geometry is Defranceschi's `/who/` page, which hand-draws a chart with its own classes. So the superseding component below is an adapter layer over the kit's chart, not a replacement for it |
| Defranceschi and Luwinski use the kit's chart | True, as does every other archive |
| Chart present: Defranceschi 50 %, Blažević 88 %, the rest 100 % | Defranceschi **1,074 of 1,961 (54.8 %)**; Blažević **1,904 of 1,904**; the rest 100 % |
| Median words per person page: 213 / 183 / 428 / 342 / 449 / 283 / 2,098 / 291 | **221 / 228 / 412 / 352 / 354 / 232 / 2,168 / 270** (Defranceschi, Falco, Blažević, Lerena, D'Arcy, Mazza, Booyzen, Luwinski). D'Arcy's sample was unrepresentative |
| Booyzen's `/people/` pages are mega-pages | Confirmed: median **20** headings per page (maximum 33), **222 of 369** pages carry 18 or more, median 2,168 words, **301 of 369 (81 %)** contain a paragraph over 120 words. The cause is not a component: the template emits one `<h2>` per site page that mentions the person, each with an excerpt, and the excerpts are harvested from the *built site* (a generator that reads its own output) |
| Section names differ everywhere | Confirmed. Only three headings are used by more than two archives: "Family" (Blažević, D'Arcy, Luwinski), "Where this comes from" (Falco, Lerena, Mazza) and "Others of the same name" (Falco, Blažević, Mazza); none is used by more than three. Distinct h2 *sequences* per archive: Defranceschi 2, Falco 4, Lerena 4, Luwinski 1, Mazza 17, Blažević 218, D'Arcy 196, Booyzen 286 |
| Evidence wording: Blažević and Lerena have none | **Wrong.** Both draw an evidence chip on every person page (1,904 and 692); Booyzen on every one of its 369. What differs is the vocabulary (section 5) |
| Images supported in five archives, not in Blažević, Booyzen, Luwinski | **Blažević does** (98 person pages with a photograph or plate, and 350 of its 856 `/found/` pages). Booyzen and Luwinski have none |
| Real photo coverage was not measured | Person pages carrying at least one photograph or plate in the body: Mazza 56 of 712 (7.9 %), Blažević 98 of 1,904 (5.1 %), Defranceschi 20 of 1,961 (1.0 %), Falco 9 of 936 (1.0 %), Lerena 4 of 692 (0.6 %), D'Arcy 1 of 473 (0.2 %), Booyzen 0, Luwinski 0. Of 1,454 distinct image files referenced from page bodies, 67 exceed 500 KB and 11 exceed 1 MB (the largest 6.1 MB) |
| Lerena prints the surname in capitals | **689 of 692**. It lives in the data (the register file), not in a template transform |
| Only Defranceschi emits `Person` JSON-LD | Confirmed: 1,869 of 1,961 (95.3 %); the other seven emit `Article` only, and Luwinski's layout emits none |
| Stub pages: Falco 5/16, Lerena 6/16 | Depends on the definition. Counting a page whose text *after removing blocks shared by 5 % or more of person pages* is under 40 words: Mazza **356 of 712 (50 %)**, Falco **167 of 936 (18 %)**, Blažević 279 of 1,904 (15 %), Defranceschi 255 of 1,961 (13 %), D'Arcy 6, Lerena 2, Booyzen 0, Luwinski 0. Lerena's six-in-sixteen is not reproduced |

Two further findings shape the design and were not in the brief:

* **A chart date can be a different fact from a birth.** Falco's chart prints, with no label, the date of the first *event* when a person has no birth or death. That is the date of the act that names them: a father's chart date can be the day his child was born. Three styles share one chart ("13 Dec 1854", "b. Dec 13 1854", "1813 – June 8 1876").
* **Colour and word answer two different questions.** Seven archives draw "the direct line" as a provenance border. It is a *result* argued on the direct-line page, not evidence of anything.

## 2. The canonical page

One order, one set of words for the headings, one anchor each. The first three always appear; if the archive has nothing for one, the page says so rather than dropping the heading, because a missing section makes a claim in silence.

| # | Anchor | Heading | Required | What goes in it |
|---|---|---|---|---|
| — | (header) | the person's name as `h1` | yes | name only in the `h1`; a qualifier ("m. … the younger, 1854") goes in a line under it; life dates in a line under that; one plain sentence of lede (also the meta description) |
| 1 | `#family` | Family | yes | the chart (section 3), or one sentence saying why none is drawn |
| 2 | `#record` | What the record says | yes | events and facts, each with its grade and its source (section 5) |
| 3 | `#sources` | Where this comes from | yes | the sources, each a link; the register query link; the count of lines resting on a tree alone |
| 4 | `#namesakes` | Others of the same name | no | people of the same name, linked only where the archive holds an id for the person |
| 5 | `#media` | Photographs and papers | no | section 7 |
| 6 | `#notes` | Notes and corrections | no | what has been corrected, left in the open |
| — | `#more-…` | the archive's own title, marked "(this archive only)" | no | anything the six do not cover, drawn after them. Allowed, counted, never passed off as shared |
| — | (footer line) | — | yes | "← All the people" · "Everyone of this name" (the `/who/` page, when there is one) · "Every record naming …" (when there is a register) |

Rules: one `h1`; sections are `h2`; nothing skips a level; no section is empty without saying so; no run of prose over about 150 words without structure. A person with several marriages, households or places uses a list or a table inside the section, not a new top-level heading per household.

### The canonical person object

The archive's adapter hands the component one object. Every field is optional.

```
person   { name, born, died, living, presumedLiving, gen, line, lede,
           birthPlace, deathPlace,
           relations { parents[], spouses[], children[], siblings[], dropped[] },
           events[], sources[], namesakes[], media[] }
relation { name, href?, born?, died?, source?, line?, ambiguous?, living?, gap?, superseded?, disputed? }
```

`href` is set only when the archive holds an id for that very person; never from a name. `dates` strings are not accepted on a relation, deliberately (section 6).

## 3. The family chart

The kit's `PersonTree` and `persontree.css` stay exactly as they are. `PersonChart` sits in front of them and does what the six adapters each did differently:

* one set of **source words** (section 5), folded from any archive's own, and **unknown words shown, not defaulted**: a word it does not know is drawn "unmarked: source word not recognised ("strong")", never as "read" or "tree";
* **dates from fields, formatted once** (section 6); never a pre-formatted string;
* **living relatives**: name only, no dates; a withheld relative is drawn as a dashed "living, withheld" node, never a name;
* **ambiguous relatives** (several people of one name, none identifiable) drawn as an unlinked node that says so;
* **an empty chart says why**, from a short code (`none-recorded`, `living-withheld`, `name-level`) turned into a sentence;
* the **direct line is a bar on top** of the node, so it can sit *with* a source border instead of replacing it;
* an honest **caption** about whether the mark is on the *link* or only on the *person* (`edgeLevel`). Mazza and Blažević mark the person today; their caption should not claim the link.

Where the chart is drawn: on the person page, always, either as a chart or as the empty statement. Defranceschi's choice not to draw one on 887 of 1,961 person pages is decision 2.

## 4. What belongs on `/who/` and how it relates

A `/who/<name>/` page is a page about a **name**, not a person: it lists everyone who bore it. It should be a short index, never a second person page.

* A name with **several bearers**: a list, each entry linking to that person's page, with lifespan and place. This is the page.
* A name with **exactly one bearer**: measured, 986 (Defranceschi), 405 (Falco), 1,109 (Blažević), 692 (Lerena, every one), 508 (Mazza), 369 (Booyzen, every one) of these pages exist, and their text overlaps their person page by a median of 1–7 %: they are not duplicate text, they are redundant doors. They should not be separate pages; see decision 2 for what replaces them.
* **Link both ways.** Measured, a person page links back to its own name page in 81 % of cases at Defranceschi and in effectively none (0 of 818 at Falco, 0 of 1,904 at Blažević, 0 of 692 at Lerena, 0 of 712 at Mazza, 1 of 369 at Booyzen) elsewhere. The canonical footer line fixes that for free.
* A `/who/` page that canonicalises to a person page must not also appear in the sitemap.

## 5. Evidence: one vocabulary, two questions

The archives use one vocabulary to answer two different questions, and a third thing (the direct line) as if it were an answer to either.

| Question | Applies to | Words |
|---|---|---|
| **Grade**: how well is this *claim* evidenced? | an event, a fact, a person | the kit's five, unchanged: Documented · Probable · Inferred · Family · Disputed |
| **Source**: where did this *link* come from? | an edge on the chart | a record read here · an index entry, not read · image held, not yet read · family tree, unverified · inferred · disputed · named here only |
| **Membership**: is this on the direct line? | a person | a flag, drawn as a bar; never a grade, never a source |

### What each archive says today, and where the mapping loses meaning

| Archive's term | Means there | Maps to | What is lost |
|---|---|---|---|
| `read`, `register`, `doc`, "a record read here", `documented` (Defranceschi, Falco, Lerena, D'Arcy, Blažević, Booyzen, Luwinski) | a person read the register act | source **read**; grade Documented | Blažević's `read` is a fact about the *person* ("a register has been read for this person"), not the link. Mapped as read, it overstates the link |
| Falco `register` + `tree` together | two independent sources agree | **read** | the agreement is lost; it survives only in the mark text |
| `index` / `indexed` | a record exists but the page was **not read** | source **indexed** | the lossiest word: Defranceschi means a FamilySearch transcription (57 % of all chart nodes), Mazza counts it as "proved by a record", Blažević calls it somebody else's transcription. Defranceschi's `/person/` page folds it into "from the tree"; Blažević gives it a class with no style and no label |
| Blažević `scanned` | an image is held, unread | source **scanned** | no grade fits: held but unread |
| `tree`, `lore`, "Testimony", `family` | the family tree, or oral account | source **tree** / grade Family | Booyzen's `lore` prints "Testimony", the kit prints "Family"; "told" and "written on a published tree" are one word here |
| `inf`, `inferred`, Luwinski "best candidate", Luwinski "read with care" | follows from a record without being stated | source **inferred** | "best candidate" is nearer *Probable*; "read with care" is a caution on a read fact, not inference |
| `disputed` | two sources disagree | source/grade **disputed** | four meanings share it: contradicted by a record (Mazza), a rejected join (D'Arcy), "corrected" and so resolved (Luwinski), a fact shown wrong (Blažević). D'Arcy's "disproved" is mapped to Disputed though it is resolved |
| `line`, "direct line", `onSpine` | membership of the direct line | **flag** | not a grade. In Lerena it also happens to imply a record was read; in Blažević it means the opposite ("no record of their own read here"). Peeled off as a flag, that distinction is lost and must be said in words |
| `open`, empty, `none` | nothing | **named here only** | there is no "unknown" level, only an absence |
| Lerena `status`, Defranceschi `conn` (yes / no / unproven) | *is this person related at all* | not a grade | a third question. The kit's `Evidence` already refuses to send `no` through as "Family" |
| `superseded`, `gone` | an edge the archive retracted, left struck through | a CSS state | no level for "retracted" |

In person data the five-level ladder is in practice three: Documented, Family and Disputed. `Probable` is produced by one archive (9 people) and `Inferred` by very few, so a five-word ladder is promised and three are used.

## 6. Dates

* Charts and tables: **13 Dec 1854**. Prose: **13 December 1854**. Never ISO ("1876-10-01"), never month-first ("Dec 13 1854"), never d/m/y digits.
* A **single date is always labelled**: `b. 1854`, `d. 1920`, `bapt. …`, `m. …`. A bare date is never printed (the cause of the unlabelled chart dates above).
* A **range** is `1854–1920`: an en dash with no spaces. (Measured: the unspaced form is the majority across the estate, about 7,000 occurrences against about 3,000 spaced.) `c. 1854` for an estimate.
* An unparseable date is shown as written and counted, never guessed.
* A chart prints **years**; the header line prints full dates.

Measured today: 338 of 369 Booyzen person pages mix "3 Mar 1843" and "3 March 1843"; Falco's chart mixes three styles; Lerena's chart prints ISO; Defranceschi's charts use the spaced range.

## 7. Images

A photograph or plate is a `<figure>` with an `<img>` that has real `alt` text (what is in the picture, not a filename), a `figcaption` (who, what, where, when, and who holds it), `width` and `height`, `loading="lazy"`, a web format, and a file under about 500 KB unless the full-size image is linked. Alt text is not the caption. **A living person's page has no photograph**, with no exceptions in the component.

## 8. Living people

The estate's rule, matching `checkliving.py`: a person is living if the archive says so by any of its flags (`living`, `presumedLiving`, a birth field that says "living") or if they were born within the last 80 years with no death recorded (strictly *more than* 80 years ago is presumed dead; evaluated at build time). A living person is published as **a name and a relationship**:

* the page is `noindex`, is absent from the sitemap, and is absent from the search index;
* no date on the chart node, none in the body, none in the description, none in structured data;
* no place, no record, no photograph, no source list;
* the description is a fixed sentence, never built from the record;
* a living *relative* on someone else's page is a name, or a dashed "living, withheld" node.

`PersonPage` enforces this by **refusing to render** the record, sources, namesakes, media and notes slots for a living person, rather than trusting each archive to have emptied them. `checkperson.py` reads the built page and fails on each leak above. Some archives publish more than this today; this spec states the strict rule, the checker counts departures from it, and whether any archive keeps a looser policy on purpose is the owner's call, outside the four decisions below. (`noindex` alone does not make a page "living": a dead person is also `noindex` when a living relative is drawn on their page.)

## 9. Stubs

A person with a name and nothing else keeps their URL (a link to it exists) and says what the page is: "Known only from *the household that names them*; nothing else is recorded yet." The page carries `data-stub`, and the empty chart gives its reason. A stub is not hidden and not padded. Whether stubs should additionally be `noindex` is left open.

## 10. Structured data

Every non-living person page emits `Person` with `name`, `birthDate`, `deathDate` (ISO, only when exact), `birthPlace`, `deathPlace`, built only from fields the page itself shows. `personAbout()` returns exactly what the existing `JsonLd.astro` accepts through `about`, which seven archive layouts already forward; no existing component changes. A living person yields none.

## 11. Cross-links

Parents, spouse, children and siblings come through the chart, linked only where an id is held. Same-name people appear in "Others of the same name" (never merged on a name alone). Sources link to the archive's sources page and to the register query. Every person page links back to `/people/` and, if there is one, to its `/who/` page.

## 12. Defranceschi's `/person/` and `/people/`

At Defranceschi, `/person/<pid>/` is a **person** (1,961 pages, 1,927 distinct after 34 declared duplicates), `/who/<name>/` is a **name** (1,737), `/people/` is the roster table (the index), and `/people/<slug>/` is nine hand-written pages about historical figures who are not family. So `/person/` plays the role `/people/<slug>/` plays everywhere else; the nine notable pages are a different page type and should not share the family person route. This is a naming mismatch inside the estate, not a content problem. Decision 2 covers what to do about it.

## 13. Decisions that are the owner's

### Decision 1 — Booyzen's `/people/` mega-pages

Facts: median 20 headings, 222 of 369 pages with 18 or more, median 2,168 words, 81 % with a paragraph over 120 words. One heading per page that mentions the person; excerpts harvested from the previous build's output.

| Option | For | Against |
|---|---|---|
| **A. Split.** A canonical person page (about 150–400 words) plus links to the existing surname, household and marriage pages | matches every other archive; ends the generator reading its own output; the page becomes readable on a phone | the generator is rewritten; a reader loses the one-page narrative; 369 pages change shape |
| **B. Keep one page, restructure.** Canonical sections first; everything else as one "Where this person appears" list of *links*, no excerpts | smaller change; stays one URL; removes the self-harvest | still a long page for some people; the list is only as good as the mention index |
| **C. Keep as is** | no work | fails every readability measure; keeps the self-referential excerpts |

Recommendation: **A**, with B's list of links in `#notes`; stop generating excerpts from the built site either way.

### Decision 2 — Defranceschi's `/person/` + `/who/`, and where the chart belongs

Facts: 887 of 1,961 person pages draw no chart because kin are recorded against a *name*, and the archive's stated reason for not drawing one is that a name page "may hold one person's dates beside another's wife". 986 name pages have exactly one bearer; 1,010 name pages canonicalise to a person page and are nevertheless listed in the sitemap. The person page folds `index` into "from the tree" and forces every child's source to empty (1,397 children print "named here only" where the data holds index 888, read 456, line 22, tree 14).

| Option | For | Against |
|---|---|---|
| **A. Keep two page kinds; fix the folding bug; add the empty-chart statement to the 887; make single-bearer name pages redirects** | respects the archive's own reason; no new claims; removes ~1,000 redundant pages from the sitemap | 887 pages still have no chart, only a reason |
| **B. Draw a name-level chart on every person page** with a caption "recorded against the name, not individually verified" | 100 % chart coverage from existing data | exactly the risk the archive refuses: another person's wife on this page, labelled or not |
| **C. Fold `/who/` into `/person/`** for single-bearer names; `/who/` becomes only a disambiguation page for shared names | one page per person; no duplicates | URL changes for about 1,000 pages; every inbound link needs a redirect |

Recommendation: **A, with C for the single-bearer pages.** Reject B for the reason the archive gave.

### Decision 3 — The single evidence vocabulary

| Option | For | Against |
|---|---|---|
| **A. One axis.** The five-level ladder for everything | simplest to explain | cannot say "an index entry, not read" or "image held, not read"; folds a transcription into Family or Inferred; keeps the line-as-evidence mistake |
| **B. Two axes plus a flag.** Grade (five) for claims, source (seven words) for links, direct line as a bar | each word answers one question; every archive's term has a home (section 5); `index` and `scanned` become honest | two vocabularies to learn; the mapping table is the maintenance burden |
| **C. Three levels.** Documented · Family · Disputed, because that is what the data uses | matches current use | gives up Probable and Inferred, which the method pages promise |

Recommendation: **B.** The library maps index and scanned to *no grade* on purpose (`GRADE_HINT`), because which grade an index entry is, is the owner's call.

### Decision 4 — Lerena's capitalised surnames

Facts: 689 of 692 names carry an ALL-CAPS token; it is in the data, not a template transform; names also carry qualifiers of up to 80 characters inside the `h1` (median 34.5, p95 57).

| Option | For | Against |
|---|---|---|
| **A. Title-case on display, keep the data; qualifier under the heading** | matches seven archives; search results and headings read the same; the qualifier stops being truncated | loses the genealogical convention that capitals mark the surname, which matters for multi-part Hispanic surnames; automatic title-casing needs an exceptions list |
| **B. Keep capitals in the chart and register, title-case in the `h1`** | keeps the convention where names are compared | two spellings of one name on one page |
| **C. Keep as is** | no work | one archive reads differently from seven; long h1 |

Recommendation: **A**, with `displayName(..., { exceptions })` for Mc/Mac and particles, and the qualifier moved. `nameStyle="asRecorded"` keeps the capitals on any page that wants them, so reversing the decision is one prop.

### Defaults chosen here that are not on the list

The unspaced en dash; "13 Dec 1854" in tables and "13 December 1854" in prose; stubs indexable; `Person` structured data on all non-living pages; six section headings. Each is a parameter or a constant in `lib/person.js`.

## 14. Adopting it one archive at a time

Nothing here changes an existing file. An archive adopts in steps, and `checkperson.py` says how far it has got at each:

1. Import `personpage.css`; swap the archive's `PersonTree.astro` wrapper for `PersonChart` (rows pass `source`, `born`, `died`; drop pre-formatted dates).
2. Wrap each existing person section in `PersonSection kind="…"` (headings and anchors become the spec's).
3. Move the page under `PersonPage`; take `title`, `description`, `noindex` and `about` from `personMeta()`.
4. Turn `checkperson.py --strict` (or `--max N` as a ratchet) on in the build.

A new commit to the kit needs each archive to repin `package.json` and `package-lock.json` together (`checkpin.py`). This branch does not change any pin.

## 15. What is on this branch

| File | What |
|---|---|
| `kit/docs/PERSON-PAGE-SPEC.md` | this document |
| `kit/docs/person-page.md` | the short README |
| `kit/lib/person.js` | the decisions, as pure functions (sections, source words, dates, living rule, names, stubs, structured data) |
| `kit/components/PersonPage.astro` | assembles the page in the spec's order |
| `kit/components/PersonChart.astro` | the chart adapter over the kit's `PersonTree` |
| `kit/components/PersonSection.astro` | one section with its fixed heading and anchor |
| `kit/components/EvidenceChip.astro` | grade and source, side by side |
| `kit/styles/personpage.css` | new classes only |
| `kit/tools/checkperson.py` | reads the built pages and fails (advisory by default; `--strict`; `--max`) |
| `kit/tools/checkperson_selftest.py` | plants one fault per rule and requires the checker to name it |
| `kit/tools/checkperson_logic.mjs` | 71 cases against `lib/person.js`, no build needed |

Not done, and left for the owner's pace: a row in `shared-pages.json` (it would change what `checkshared.py` reports for every archive), regenerating `docs/components.md` (it is two components stale already), wiring a `check:people` script into any archive, and repinning anything.
