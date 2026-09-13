# The Archive Kit

The pieces that are identical in all seven family archives, kept in one place
so they cannot quietly drift apart.

    The Defranceschi · The Falco · The Blažević · The Booyzen
    The Lerena · The D'Arcy · The Mazza

## What is in here

| File | Lands at | What it is |
|---|---|---|
| `kit/components/Evidence.astro` | `site/src/components/` | The five-word evidence ladder: documented, probable, inferred, family, disputed. Every older label each archive used is folded in as an alias, so nothing breaks. |
| `kit/components/SiblingArchives.astro` | `site/src/components/` | The ring — every archive except the one you are standing in, worked out from `BASE_URL`. |
| `kit/data/archives.json` | `site/src/data/` | The seven archives: name, address, accent light and dark, where, one line, surnames. The single source of truth for the ring, and for the children's site. |
| `kit/tools/sitemap.py` | `tools/` | Writes `sitemap.xml` from the built HTML, skipping anything that noindexes itself — so living people's pages can never be handed to a search engine by accident. |

CSS is **not** copied. Each archive's stylesheet is its own; the kit only
checks that the blocks it needs are present (`.ev-documented`, `.ladder`,
`.ring`, `--ev-inferred`) and says so when one is missing.

## Using it

    python3 sync.py --check     # say what has drifted, change nothing
    python3 sync.py             # copy the kit out to all seven

## Why a copier and not a package

A shared npm dependency is the tidier answer and the wrong one here. These are
seven static sites that deploy straight from a push, worked on by several
people at once. A dependency means one bad publish can take all seven offline
in the same minute, and a resolution failure in CI is an outage rather than a
warning. A copy that is checked costs one command, fails loudly, and never
fails everywhere at once.

If that trade stops being worth it — if the kit grows to the point where
copying is the bottleneck — `sync.py` is the file to replace, and nothing else
has to change.

## What belongs in here next

Two build guards that already exist in one archive each and should exist in
all seven:

- **`check_release.py`** (Falco) — fails the build if any living person carries
  a date or is left indexable. The privacy rule enforced by machine rather than
  by memory.
- **`regen.py --check`** (Blažević) — hashes every derived data file and fails
  the build if one has drifted from the tool that makes it. It caught a real
  inconsistency within minutes of one being introduced.

Neither is copied yet because each is written against its own archive's data
shapes. Generalising them is the next piece of work.
