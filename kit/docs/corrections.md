# The corrections page, and how /whats-new/ points at it

`components/Corrections.astro` draws the page; `lib/corrections.js` is what it and `/whats-new/` (`lib/pulse.js`) must agree on.
Changed 17 Nov 2026 after David's five questions on the Defranceski page; it applies to all eight archives.

| David asked | what the kit does now |
|---|---|
| why are they not sorted by date, newest first? | The component sorts by `when` itself (`sort="date"`, the default). A date it cannot read goes after the dated rows; rows on one day keep the archive's own order (so an archive may still put the serious ones first within a day). `sort="given"` keeps the archive's own order. Do NOT pre-sort the rows by severity in the archive's page: that was the cause. |
| the What's new card goes to the page, not to the correction | Each correction has an anchor, `c-<day>-<hash of the headline>` (`corrIdMap(rows)` in `lib/corrections.js`). `buildPulse` links the card to `/corrections/#<anchor>`; the page puts the same anchor on the entry (`id:` in each row) and highlights it. If a filter is hiding the entry, the page clears the filters first. |
| the date of a long day gets lost | One heading per day (a day is now ONE group, because the rows are sorted), and the heading stays at the top while its entries scroll under it. An archive with a fixed header sets `--cx-top` to its height. |
| who is this about? | A row can carry `for: [["/people/slug/", "Name"], ...]` (the same list a search row uses: the archive's own pages for the people, never a person it does not publish). The page shows "About Name" on the entry (map it to `about:`), and the What's new card shows it under the headline. The kit does not guess a name: a row with no `for` names nobody, and the card says nothing. |

## What an archive does (about ten lines in its own `corrections` page)

```astro
import { corrIdMap } from "@daviddef/archive-kit/lib/corrections.js";
const ids = corrIdMap(c.rows);              // c.rows in FILE order, the same list the build passes to buildPulse as `corrections`
...
<Corrections rows={c.rows.map((r) => ({ ..., id: ids.get(r), about: r.for }))} />   // no sort of its own
```

The `ids` must come from the SAME rows `buildPulse` gets (`corrections: c`), in file order; otherwise the anchors do not match and the card falls back to the top of the page.
Putting a `for` on each correction row is the archive's work, from its own data: who the correction is about, one page per person, the archive's own pages only.
`node kit/tools/corrections_logic.mjs` holds the anchors, the order and the card links to cases.
