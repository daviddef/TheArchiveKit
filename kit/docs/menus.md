# The header menu: the shape every archive converges on

23 November 2026. David decided it after the estate audit of 22 Nov (`archive-review.md`); the Booyzen menu of 12 Nov is the reference.
The Research tab is separate: see [research-menu.md](research-menu.md).

| Group | What it holds |
|---|---|
| Start | Home, The story, About |
| Our line | the archive's own line pages (its own voice; no cap) |
| People | **Lists** (People, Every Name, The Register, Households where held, Marriages) and ONE link, **Drawn**, to a hub `/drawn/`. The tree, the trees, blood relatives, the timeline and the direct line are listed on the hub, each with one line saying what it shows. |
| Places & families | Places (with The Lines and The Atlas) and the families as **one hub link "All the families"** plus at most four named families: the archive's own line first, then others A to Z (David, 12 Nov 2026). Every family page that leaves the menu is linked from `/families/`. |
| The name | The Name, The forenames. Every archive has this group. |
| Research | the eight core pages in the three groups of research-menu.md, plus ONE "Deep dives" sub-group whose heading links to a hub listing every local study, check and deep dive. About 12 to 14 links. |

## How a hub is built

With the archive's own `Base` layout and the kit's `ResearchList` (`items=[{href, label, blurb}]`), reading the same JS list that draws the menu, so the menu and
the hub cannot disagree. A hub is an ordinary page: indexable, in the sitemap and the search index.

## Nothing may fall out of reach

A page that leaves a menu must still be linked from a hub. Prove it with `kit/tools/menu_inventory.py` (`snapshot` before, `compare` after) and keep the proof
in the archive's `docs/menu-reach.md`.

## What stays archive-local

The menu list itself, the counts, the hub pages' words. An archive that is smaller (Luwinski) may have a shorter menu but uses the estate's labels where it has the same page.
