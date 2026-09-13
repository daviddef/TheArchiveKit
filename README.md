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

## The search contract

Every archive builds its own index — only an archive knows its own data
shapes — but all seven emit the same rows, because one component reads them
all:

| field | meaning |
|---|---|
| `k` | kind — the group a hit belongs in: Person, Place, Record, Page… |
| `t` | title, what to show |
| `s` | subtitle: dates, a place, a reference. May be empty |
| `h` | href, site-relative, beginning with `/` |
| `q` | haystack: title + subtitle + body, lowercased and accent-folded |

A generator that emits anything else should normalise on the way out rather
than at read time, so the fix cannot drift back. Four of the seven already
emitted this; the other three now convert in their own build scripts.

## Why it was a copier, and is not any more

It started as a copier, on the argument that one bad publish should not be able
to reach seven live sites in the same minute. That argument has not gone away.

What changed the balance is that the copies began to matter. The evidence
ladder, the ring of sibling links and the search contract are things that have
to *agree* across archives to mean anything at all — a ladder that says
something different on the Falco site than on the Booyzen one is worse than no
ladder. Agreement by convention lasts until somebody edits one copy.

So the components are installed now, and the risk is real: `npm install`
reaching GitHub is a dependency all seven builds share. The mitigation is that
the kit is small, has no dependencies of its own, and is pinned by
`package-lock.json` in each site — a bad publish does not reach a site until
that site reinstalls.

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
