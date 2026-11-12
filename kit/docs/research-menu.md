# The Research menu

12 November 2026. David chose it; the Defranceski archive built it first (TheDefranceski PR #4), seven archives followed
(Booyzen, Luwinski, Lerena, D'Arcy, Falco, Blažević, Mazza).

**One Research tab replaces Evidence and Investigations**, in three groups, plus an optional fourth:

| Group | Core pages (the eight the estate always carried, labels unchanged) | Local, allowed |
|---|---|---|
| To do | Open Questions, Errands, The work list | |
| What's new | What Has Been Read, Corrections, What changed | the archive's /whats-new/ as the group page |
| Sources & method | Sources, Method (and Documents, Gallery where held) | Deep dives (a study of one source, linked from its row on Sources); pages whose registers and places the Record Atlas also carries |
| Checks (optional) | | Generated audits of the archive against itself |

## What the kit now holds

- `data/research-menu.json`: the canon, read by `checknav.py --canon research`. Same eight core pages, same labels; the core pages are
  read **in the order of the groups**, and an archive's own pages may stand in the menu (reported as local, not a departure).
  `evidence-menu.json` stays the default until all eight archives have moved.
- `components/AtlasNote.astro`: the note at the top of a page whose registers and places are also on the Record Atlas.
  Replaces six local copies. Link only Atlas pages that return 200.
- `components/ResearchList.astro`: the list of pages with what each asks. The archive passes `blurb` (it knows its own counts).
- `tools/menu_inventory.py`: the "nothing lost" check. `snapshot` the old build, `compare` against the new one, `sitediff` the whole
  site; page text is stored as hashes (a page that names a living person tripped `check:living-years` when the before-inventory
  held text). An archive lists its in-scope pages in `docs/menu-scope.json`.

## What stays in the archive

The menu list itself (`lib/research-menu.js`), the counts (`lib/research-counts.js`: each archive's data has its own shape), the
hub and group pages, and its `menu-canon.json` until it points `check:nav` at `--canon research`.

## Moving an archive over

1. `npm install` the kit version that carries this; `check:pin`.
2. Replace the local `AtlasNote.astro` and `ResearchList.astro` with the kit's (`@daviddef/archive-kit/components/...`); pass `blurb`.
3. `check:nav`: `checknav.py --dist dist --canon research`, then `--strict` once it conforms; delete `menu-canon.json`.
4. Nothing else changes. Vocabularies (outcome words, severity) are NOT part of the menu and are not touched.
