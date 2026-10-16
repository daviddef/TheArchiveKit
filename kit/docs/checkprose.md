# checkprose.py: the living standard, enforced on hand-written pages

`kit/tools/checkprose.py` (self-test: `checkprose_selftest.py`, 34 cases) fails when a hand-written page, a hand-edited
data file or a note says more about a living person than the standard allows: name, relationships, full town and
country, and nothing else. `checkliving.py` guards the built pages against the dates the data attaches to a living
person; this guards what somebody typed.

## Wiring it into an archive

1. Write a feed OUTSIDE the repo (a living person's name never goes in a tracked file for a gate). One entry per
   living person, from the archive's own data and `living_rule.py`, plus the names of everyone else the archive
   publishes, so a living person who shares a name with an ancestor is skipped and counted, not guessed at:

        {"living": [{"id": "p123", "names": ["Given Family", "Given Middle Family"]}],
         "deadNames": ["Given Family", ...]}

   `deadNames` must come from IDENTITY (the archive's dead rows), never from "every name that is not in the living
   list": a living person and an ancestor with the identical name would then cancel each other out of the corpus.
2. Run it after `git add` (it reads tracked files, and fails on a matching file that is not tracked):

        python3 node_modules/@daviddef/archive-kit/kit/tools/checkprose.py --root . --feed ../private/living-feed.json \
            --include site/src/data/sources.json --include site/src/data/corrections.json

   By default it reads site/src/pages, site/src/content, notes/, docs/ and top-level markdown. Hand-EDITED data files
   are named with `--include`; generated data stays with its generator's own scrub gate. `--allow-keys` lists the JSON
   fields a living record may carry if the archive's model needs more than the default (name, relationships, place).
3. A true false positive (the author's name beside the date a document was retrieved; a living name in one sentence
   and an unrelated 1863 baptism in the next) goes in an allow file, one reasoned entry each. An entry that matches
   nothing fails, so the list cannot go stale. Never loosen a pattern instead.

## What it does and does not do

- Fails on a year (1800-2099), a full date, a month and year, a slash date or an ISO date, or a life-event word
  (died, buried, baptised, christened, funeral, obituary, aged), within 150 characters of a living name inside one
  paragraph / list item / table row / JSON string. In a JSON record whose name field is a living person's, any field
  outside `--allow-keys` fails.
- A year inside a URL or id is counted and printed, not failed (a slug such as `/person/anna-rossi-1846/` still tells a
  reader a birth year; that is a naming decision for the archive).
- It never prints a name, a year or a date: the log carries the file, the place in it and the KIND of problem.
- It refuses to pass on nothing (empty feed, no matching file, untracked match) and plants a living name beside the
  year 1899 in a temporary file before every real run, refusing to run if it does not catch it.
- It is a proximity test on names. It cannot know a sentence's subject, so it errs toward flagging, and it cannot
  separate a living person from an ancestor who shares the exact name unless the feed lists the ancestor.
  It does not read images, PDFs or built HTML (checkliving.py and each archive's own gate cover the built site).
