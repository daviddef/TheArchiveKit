# Traps this estate has fallen into more than once

Written 21 September 2026, out of two days in which eight sessions found the
same faults in each other's work. Each entry is a real instance with a real
number, because a trap described in the abstract is one nobody recognises when
they are in it.

## A short token inside a long word

**Four instances, three of them mine.**

- `istra` matched inside **ADMINISTRATION**, and a Cape farm was accused of
  being in Croatia.
- `eire` matched inside **FIGUEIREDO**, and a woman born at Lourenço Marques
  was accused of being in Ireland.
- `jan` folded into `johannes`, and because every date here writes January as
  *Jan*, **338 of 346 people** matched a search for JOHN.
- `nati` matched inside **ANTENATI**, and every row in a staleness report
  classified as a birth row. Six of twenty-two hits died with one substitution.

It fails in the direction of MORE hits, which is the direction that looks like
the tool working. Match on word boundaries, and when a token is short enough to
live inside an ordinary word, put it on a stop list and say why.

## A check that inspects nothing and reports all clear

- A country gate wired into an archive whose place names are bare — *Cradock*,
  *Indwe* — printed **ok** having tested zero places.
- A living check reported **876 pages checked** over a dist a killed build had
  left empty.

Nothing distinguishes *found nothing* from *looked at nothing* unless the tool
says which. Print the denominator, and refuse when the input looks unfinished.

## A check that tests something else and reports it as this

The section above is about a check with nothing in front of it. This one is
worse, because the denominator is fine: the check runs, reads a real object,
returns a well-formed answer — and the object is not the one anybody thought
it was reading. **Eight of these surfaced across two sessions in a single
day, 21 September 2026.**

- **Two runs of a generator, both reading the same `dist`.** Byte-identical,
  and it proved the code was deterministic, which was not the question.
  Across a rebuild: **347 of 347 dossiers changed**.
- **A comparison that iterated dict keys.** `sorted(json.dumps(x) for x in
  a[k])` where `a[k]` was the dossier *dict*, so it walked `n`, `slug`,
  `mentions`, `pages`, `hits` — identical for every person in the file. The
  "reordered only, nothing changed" branch **could not fail**. Redone against
  `hits`: 0 reordered-only, **345 content-changed**.
- **A build taken before the change existed**, then `check:worklist` and a
  JSON parse reported as verification. Neither touches the schema that broke.
  The next build died and took 687 rows of `/searched/` with it.
- **A filter that displayed one thing and applied another.** FindAGrave's
  `locationId=country_204` is **Malawi**; the page rendered a chip reading
  "South Africa". Dropping the id ignores the filter entirely and returns
  7,116 results from Germany, the USA and Egypt — still under a "South
  Africa" chip.
- **A count read out of a JavaScript dictionary.** "0 memorials" appeared
  twice in a fetched page; both were i18n strings. The real results were
  rendered client-side and were not in the document at all.
- **A null out of an HTML error page.** `archive.org` serves `_djvu.txt` for
  a lending-restricted book as **HTTP 200 and an error page**; 22 of 22
  "downloads" were that page, and a script checking only for a non-empty file
  counted every one a success.
- **Existence-and-parse run against a stale artefact.** A search index with
  12,064 valid rows passes every check and is a generation behind.
- **A grep that counted a string occurring lawfully in another column** —
  and this was the most convincing of the lot, because it *was* a
  measurement. `grep -c '"NOT READ"'` returned 1 for one commit and 2 for
  the next, so the 1 was read as the defect. `NOT READ` is a legal value in
  the verdict *headline* column and had sat in an unrelated row for days.
  The check that settles it reads the **position**: parse, and count rows
  whose badge slot is outside the five the map allows — 0 and 1, not 1 and
  2. **A measurement of the wrong column is not a measurement of the column
  you meant.**

The shape is always the same and it is never loud: **a plausible answer about
the wrong object.** A wolf-crying gate gets fixed the day it is written; this
kind is believed for months.

Two habits catch it, and neither is a code review:

1. **Name the object the check actually read, out loud, and say how you would
   know if it were the wrong one.** "Both runs read the same `dist`" ends the
   first case in one sentence.
2. **Prove the check can fail. Inject the fault and watch it fire.** The
   duplicate-anchor check was written against a real duplicate; the
   dossier-drift gate was tested by injecting a two-hit drift and confirmed
   silent otherwise. A check never seen to fail is a check with no evidence
   behind it.

And the corollary for a null: **a zero from an object you have not verified
is not a negative, it is no result.**

## A many-to-one fold that assigns instead of reducing

Source rows are often one-per-series, one-per-record, one-per-sitting, and a
map wants one answer per place. The join is written in a loop, and the loop
says `=`.

- Mazza's shelf layer set a comune's colour from `coverage.json`, which holds
  **one row per series**. Piedimonte Etneo has **six `open` rows and one
  `route`**, and the line was
  `cats.setdefault(head, {})["shelf"] = SHELF[row["status"]]`. **The colour
  was therefore decided by whichever row happened to sit last in the file.**
- It rendered correctly on the day it was written, for all seven comuni. It
  would have turned Piedimonte green the moment anybody appended an `open`
  row beneath its `route` one — **a silent change of published meaning caused
  by the order of a data file**, with no error and nothing to notice.

**A fold needs a rule, and `=` is not one.** Decide what many rows mean about
one place and say it: the worst status, the earliest date, the count, the
union. Mazza took the worst on an explicit ranking.

**The test is reverse the source file and re-run — but compare the facts, not
the bytes.** This entry first said a byte comparison "distinguishes the two
cases exactly". It does not, and the Mazza session found out by running it
over eight builder/input pairs: **six of the eight "failed" and every one was
benign.** Most builders emit a *list* in file order, so reversing the input
reverses the list and the bytes differ for a reason that is presentation
rather than data loss. Acting on that would have meant rewriting six correct
builders.

The discriminator is that **a fold losing a row shows up as a changed value
or a vanished key, never as a reordering.** So canonicalise both outputs
before comparing — sort every list by its own contents — and diff the set of
facts:

    python3 - <<'EOF'
    import json, subprocess
    def canon(o):
        if isinstance(o, dict):  return {k: canon(v) for k, v in sorted(o.items())}
        if isinstance(o, list):  return sorted((canon(v) for v in o),
                                               key=lambda v: json.dumps(v, sort_keys=True))
        return o
    a = canon(json.load(open(OUT)))          # build, then
    # reverse the source rows, rebuild, and:
    b = canon(json.load(open(OUT)))
    print("fold has a rule" if a == b else "the file's order is deciding")
    EOF

With that, six false alarms became the one true finding.

**And do not wire it into a build.** It rewrites tracked input files and
restores them in a `finally`, which survives an exception and not a kill — a
build killed mid-check leaves a reversed data file sitting in the tree looking
like an ordinary edit. Keep it a deliberate `check:order`. (The same session's
first `reverse_rows` read the file *inside* `open(src, "w")`, which truncates
first; the restore is the only reason that cost nothing.)

Not every keyed assignment is this. `out.setdefault(place, {})[arkID] = {...}`
in Booyzen's and Blazevic's atlas builders is a **dedupe on a unique key**,
where a second write carries the same value; both were checked when this was
found and neither is affected. The fault needs a *many*-to-one relation, which
is why it is worth naming the relation rather than the syntax.

## Counting files instead of reading them

- Four archives were reported ready for a second map layer because they had
  `graves.json` and `coverage.json`. Read properly: the graves are keyed to
  cemeteries with plot references (**18 of 89** match a place), and the coverage
  files are per-person, per-database and per-document. One was a map of a film
  reel.
- A year filter was nearly built on a `when` field holding **"Town, Cape
  Colony"**.
- A field called `people` held occurrence counts and disagreed with its own
  bearer count in **21 of 39 rows**.

A field name is a claim about its values. Open it.

## Work that exists, is correct, and reaches nobody

- Evidence keyed to a person by slug, with no page reading the file.
- A fold map generated on every build and passed to no component, so the
  register it was written for searched raw text.
- A search box driving a script whose elements had been deleted, beside a
  working filter.
- A `?q=` prefill that set the box and never called `apply()`.

## And the better test for that last one

Not *are there two paths, one broken* — the covering path can be the **same
path, earlier in the file**. A note that answers wrongly at the top and
correctly at the foot leaves every tool that reads it finding something true.

**Can a reader stop early and be wrong?** If yes, the fix is structural: make
them meet the correction first. Detecting that one sentence contradicts a later
one is not something a build should attempt; insisting the withdrawal comes
first is cheap and always satisfiable.

## A generator that reads its own output

- Booyzen's `dossiers.py` scrapes every built page for mentions of a person and
  writes the excerpts back into `dossiers.json`. Person pages then **print those
  excerpts verbatim**, one `<p>` each — so **7,307 of 9,008 excerpts, 81%, were
  harvested from pages that are nothing but the previous run's output**.
- It never had a stable value. Generate, rebuild, generate again and **all 347
  dossiers changed**, total mentions 24,981 → 24,636. Which excerpt a reader saw
  was arbitrary.
- The visible symptom was smaller than the fault. Person pages head themselves
  "*N mentions across N pages*", so **1,732 excerpts, 19%, quoted a count the
  tool itself had written**. Stripping those counts did what it said — quoting
  excerpts fell **1,732 → 1,370** — and moved the churn only from **347 of 347
  to 343 of 347**. The counts were a symptom; the substrate was the excerpts.

**Two runs of a generator are not a convergence test** if both read the same
`dist`. They will agree, and prove only that the code is deterministic. The test
is **generate → rebuild → generate → diff**, and it is the only one that can
fail.

A cheaper standing check, where the output is rendered back: compare what the
data file stores against what the built pages print. Booyzen stores 9,008
excerpts and its pages print 8,972 — and one person's page prints **more** than
the file holds, which no rendering filter can do. That gap is the drift, and it
should be zero.

**Excluding the generator's own pages has to be done by section, not by route.**
`dossiers.py` already skipped `/who/` and `/places/`, which are wholly
generated, and `gallery.py` in the same repository skips `/gallery/`. Person
pages were missed because they are not wholly generated: the dek, the eyebrow
and the prose all come from source and legitimately name other people. Only the
printed-excerpt block is output, so only that block can be cut.

Swept across the estate, 21 September 2026. Tools that read `dist` **and** write
data rendered back into it: Booyzen's `dossiers.py` and `gallery.py`, of which
`gallery.py` already guards itself. The four search indexes — Booyzen, Blazevic,
Mazza, Luwinski — are **fetched at runtime and never inlined**, so their output
never becomes page text and cannot come back. Falco's, Lerena's and Blazevic's
`dist` readers are checkers that write nothing. D'Arcy, Defranceschi, Our Family
and the Record Atlas have no tool that reads `dist` at all. **One archive had
it, and the other seven are clean by construction rather than by luck.**

## The evidence for a fault is usually in the set, not the case

- Thirteen clusters yesterday and six today: the number changed, no single
  cluster looked wrong.
- Frames read as 1741, 1746, 1747 were 1711, 1716, 1717 — every frame plausible
  alone, the **run** impossible.
- Four database queries failed and all four shared a character; none of the
  successes did.
- COSSI and CIOFFI told apart by a ligature shape that three readings in one
  volume showed to be the scribe's habit and not the name's property.

## When a gate must be a report

A staleness report pairing *still to try* against *already read* finds real
overlaps — sixteen in twenty-three rows in one archive — **and a row may be
re-reading a volume on purpose**, at higher resolution, because a survey is not
a reading. A gate would refuse that build and the fix would be to stop
recording honest re-reads. Overlap is a question for a human.

## A broad `git add` does not steal work, it steals the reason for it

Booyzen row 160 already said never to stage everything in a repository two
sessions edit. On 21 September 2026 it happened three times in one afternoon,
to the same session, from two different archives.

- Falco `c92822d` — "SARA RUGGIERO WAS A MIDWIFE" — carried another session's
  conversion of `sources.astro` to the kit component, and its kit repin.
- Falco `1883f86` — "1817 was published as «No Falco» and holds two" — carried
  the rewrite of that same file, +17/−2.
- Booyzen `e212628` — "The stale-index trap documented" — carried four
  work-list rows about the estate's sources pages.

**Nothing was lost. That is not the damage.** Every line survived byte for
byte, and in all three cases the change was already verified green. What was
lost is the only thing these commit messages exist to carry: a reader running
`git log -S` on "why did the sources page change" arrives at a commit about a
midwife. The estate keeps its reasoning in its history rather than in a
tracker, so a sweep that files work under an unrelated heading does more harm
than a merge conflict, which at least announces itself.

The tell is cheap and was available before every one of these: `git status`
before staging, and stage **named paths**. A file you did not touch this
session is not yours to commit, however clean the diff looks.

## The gate caught its author within the hour

`checksources.py` landed on 21 September 2026 and its first real finding was
against the person who wrote it.

Twelve of Mazza's twenty-five sources were given urls, verified one by one,
and written into `site/src/data/sources.json`. The build then reported **25 of
25 unreachable**. Nothing had gone wrong with the gate: `tools/build_sources.py`
regenerates that JSON from `data/sources.tsv` on every build, and had simply
written the file back without them.

Two things worth keeping from it.

**A generated file is not a place to put a fact.** The estate already had
«a generator that reads its own output» written down; this is its neighbour,
and the tell is the same — ask what writes a file before editing it, not after.
One grep over the estate settled the rest: only Mazza and Booyzen generate
their `sources.json`; Falco, Blazevic, D'Arcy and Defranceski hand-maintain
theirs, so the same edit was safe in four archives and silently useless in two.

**This is what a gate is for and it is the only reason it was noticed.** The
page would have rendered perfectly — twelve missing links look exactly like
twelve sources that never had one. Nothing was broken, no test failed, and the
loss would have been invisible on screen. A check that can only be satisfied
by the data being right is worth more than one that checks the output looks
right.

## A page is not a component, and nothing was watching pages

`checkshared.py` has watched duplicated COMPONENTS since 14 September 2026 and
would never have found the worst duplication in the estate, because the thing
duplicated was a page.

Falco, Blazevic, Mazza and D'Arcy each carried an 85-line
`places/[slug].astro` **with the same md5** — not four similar pages, the same
file, including the comment explaining why it existed. `checkpages.py`, written
on 21 September, found it on its first run and ranked it above everything else.

The rest of that first run is the shape of the problem: **37 page names carried
by three or more archives, and 67 archive-pages still drawn by hand** — `dna`
six times over 3,681 lines, `name` seven times over 1,846, `people/[slug]`
seven times over 1,676.

Two rules came out of it.

**Two archives sharing a page is a coincidence; three is a pattern.** Below
three there is nothing to promote and the shared thing is imaginary. At three
the copies have already started to drift, and the drift is invisible because
nobody diffs pages across repositories.

**The check that finds this must discover its own subjects.** `components.py`
kept a hand-written list of archives, spelled one of them with the wrong case,
and omitted Luwinski entirely — so for as long as Luwinski has existed, every
count it printed was short by one archive and nothing Luwinski called was ever
credited. `checkpages.py` globs for `*/site/src/pages` instead.

## A check that reads outside its own repository is not a build gate

`checkpages.py` compares an archive's pages against the other archives'. It
needs the estate on disk beside it. **A GitHub Actions runner checks out one
repository and nothing else**, so on a runner the comparison set is empty —
and the first version treated empty as a failure and returned 1.

It was wired into eight builds and **broke the deploy of every archive in the
estate within eleven minutes**. Local builds had all passed, because locally
the estate is always there.

The fix is one line of judgement, not of code: **fewer than two archives found
means the check COULD NOT LOOK, which is not the same as finding nothing
wrong.** It says so and exits 0, and still fails loudly wherever the estate is
actually present. The same distinction the sources gate needed, pointing the
other way — that one had to fail when it could not find its subject, because
its subject is inside the repository and an absence there is a real finding.

The rule worth keeping: **before putting a check in the build chain, ask what
it reads.** In-repo, it can fail on absence. Out-of-repo, absence is normal
half the time it runs, and a gate that cannot tell those apart will eventually
block every deploy at once.

It was caught by another session reading the run log, not by the session that
wrote it — which is its own lesson about pushing a new gate to eight
repositories before watching one deploy finish.

## Passed locally, failed on the runner — twice in one day, two different causes

Both broke deploys across the estate on 21 September 2026 and both were
invisible where the work happened.

**The loud one.** `checkpages.py` compares an archive against its sibling
archives. A runner checks out ONE repository, so the estate is empty there;
the first version read that as a failure and returned 1, and eight deploys
stopped within eleven minutes. Its own entry above has the rule: a check that
reads outside its own repository is a dev-machine check, and if it must sit in
the build chain it has to know the difference between «nothing is wrong» and
«I could not look».

**The quiet one, five hours earlier.**

    python3: can't open file '.../kit/tools/checksources.py': No such file

A gate was wired into `package.json`'s build chain while that archive's kit
pin still named a commit from before the gate existed. It ran locally because
the working copy of `node_modules` had been installed by hand from a newer
sha. CI installs from the committed pin and found nothing there.

Nothing is wrong with the script, the package.json or the pin ON THEIR OWN.
They only disagree once somebody else installs them — which is to say, never
on the machine that can see the problem.

`checkpin.py` is the answer to the second: every kit path a build script names
must exist, and **the lockfile must have resolved the commit package.json
pins**. The lockfile is the only place npm records what it actually fetched —
the installed package.json has said `1.0.0` for months. Both faults were
reproduced on a copy before the check was trusted.

The habit both want: **after wiring a tool into a build, push and watch one
deploy finish before wiring it into seven more.**
