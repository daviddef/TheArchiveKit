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
