# What's new, the numbers and the search box

Three things every archive's header and one page carry, built once here (first in the Defranceschi archive, 11 November 2026):

| piece | file | what it is |
|---|---|---|
| the ribbon | `components/PulseRibbon.astro` | round buttons in the top nav: a sparkle to `/whats-new/`, a chart that opens a panel (the four newest cards and the archive in numbers), a magnifier that opens the search box |
| a day's rows | `components/WhatsNewDay.astro` | one day of `/whats-new/`, laid out as Record Atlas lays out a research day: the day's searches grouped by provider (the text of `src` before its first dash, comma or colon), each group with its tally, rows of source name (a link to the row's own `url`/`href`/first of `urls` when it is an http(s) address, else to the archive's page that tells it, else to the log), place, ✅/❌ pill and pages; first ten rows shown, the rest under «Show the other N» |
| the search box | `components/SearchPop.astro` | the instant pop-up over the page: results as you type from `/searchindex.json`, arrow keys, Enter, Esc, `/` or Cmd/Ctrl+K from anywhere, «Open the whole list» to `/search/` |
| the page | `components/WhatsNew.astro` | the body of `/whats-new/`: a tally with filter badges, one card of numbers, a timeline (a rule down the left, the date on it, a card per change) |
| the logic | `lib/pulse.js` | `buildPulse()`: the log and the corrections list in, days and cards and counts out; pure functions |

Nothing is written by hand. The pulse is computed **at build time** from the archive's own search log (`searched.json`), corrections list and work list, so there is no generated file to go stale. A row of the log with a date and an outcome becomes a line; the day's searches fold into one «Research» card that opens onto its rows; each correction is a card of its own.

## Wiring it into an archive (four small files)

1. **`src/lib/pulse.js`** (the adapter, the only archive-specific code):

```js
import { buildPulse } from "@daviddef/archive-kit/lib/pulse.js";
import searched from "../data/searched.json";
import corrections from "../data/corrections.json";
import worklist from "../data/worklist.json";
import people from "../data/people.json";
export const pulse = buildPulse({
  searched, corrections, worklist,
  counts: { people: people.length, sources: 0 },     // the two numbers no log holds
  // fields: { when: ["date"], what: ["scope"] },     // only if this archive names a column differently (see FIELDS in lib/pulse.js)
  // outcomeMap: { done: "found" },                    // only for an outcome word the kit does not know
});
```

2. **`src/pages/whats-new.astro`**: the archive's layout around the kit body:

```astro
---
import Base from "../layouts/Base.astro";
import WhatsNew from "@daviddef/archive-kit/components/WhatsNew.astro";
import { pulse } from "../lib/pulse.js";
---
<Base title="What's new" eyebrow="Fresh from the workbench" dek="…" noautolink>
  <WhatsNew pulse={pulse} tries="a place, a name" />
</Base>
```

3. **`Base.astro`**: `<PulseRibbon pulse={pulse} />` inside the top nav (replacing the old «Search» pill, class `findbtn`), `<SearchPop tries={["a name", "a place", "a year"]} />` once after the header, `data-search-open` on the drawer's Search link, and «What's new» in the menu. If the layout has its own «/» shortcut it must step aside when `#sdlg` exists.
4. **`book.json`**: `/whats-new/` under `outside`, or as a chapter (`checkbook` refuses an unplaced page).

The page is a **template use, not a bespoke page** (`checkpages --max-bespoke 0` counts a page that carries its own markup). Put `noautolink` on the layout call: the cards quote the log's own text and a name inside it must not be linked by the build.

## Under each row: the Atlas and the pages updated (optional, 12 November 2026)

An archive can show, under each search row, whether the Record Atlas has it and which of its own pages the finding went into, with a gate that new found rows name one:
**[whats-new-receipts.md](whats-new-receipts.md)** (`lib/receipts.js`, `tools/check_row_pages.py`). An archive that does not wire it renders exactly as above.

## What it reads, and what it leaves out

`rowsOf()` takes the log as an array, as `{rows}` or as `{searched}`, and skips a row with `_note`. A row becomes a line only if its **date is a day the work was done**: `2026-11-11`, `11 Nov 2026`, `5 October 2026`, `Sept 2026` (a month alone shows no day). A bare record year (`1814`) or a sentence is not a date and the row stays on the archive's own log page, counted in the footer of `/whats-new/` («N of M log rows carry a date this page can read»). A date more than **one day after the build's UTC day** is a typo and is left out; a date **one day ahead is kept**. A researcher writes the day's date as their own local day, and in Australia (UTC+10/11) that is already tomorrow in UTC for up to about eleven hours, so without the day of grace every row dated «today» was hidden from `/whats-new/` until the first build after 00:00 UTC (Falco's two 13 Nov rows were hidden this way on 12 Nov, 22:11 UTC). One day covers every time zone up to UTC+14; two days ahead is still a typo. The same rule applies to the corrections' dates. `latest` (the header's «to 13 Nov 2026», the panel's «What's new to …») is the **newest work date in the log**, so on such a build it can be the day after the build date; «In the seven days to <date>» and the panel's «this week» count the seven days ending on that same `latest`, so a row dated a day ahead is the newest day and is in the week (the oldest day of the seven drops out a day sooner than it would otherwise). `buildPulse({ today })` overrides the build day (the tests use it); the tolerance is `dayAfter(today)` in `lib/pulse.js`. **An outcome word the kit does not know is left out, not guessed** (`outcomeMap` adds one); `OUTCOME` in `lib/pulse.js` holds the dozen words the eight archives have used for yield / nothing / partial / blocked. Counts that are zero are not shown.

It prints only what the archive's own log and corrections pages already print, clipped. It counts people, never names one, and adds nothing about a living person that those pages do not hold; the archive's own living-people gates (`checkliving`, the archive's own prose rules) still run over the built page.

## The gates

* `node kit/tools/pulse_logic.mjs` (in `npm test`): the library against cases written from the eight archives' real shapes, and planted faults (a date more than a day ahead, a bare year taken as a date, a `_note` row taken as a search, zero counts shown) each shown to fail the case it guards.
* `python3 kit/tools/checkpulse.py --dist dist` (add `check:pulse` to the archive's build, after `astro build`): `/whats-new/` is built with a timeline; the «N searches» and «N corrected» badges equal the rows and cards drawn; every card links to a built page; the home page and `/whats-new/` each have exactly one ribbon, one search box (`#sdlg`), a link to `/whats-new/`, a `data-search-open` button, and no old `findbtn` pill. `--selftest` plants each fault in a tiny site.

## Per-archive notes (how each archive's log reads today)

* **Lerena, Luwinski, Booyzen**: ISO dates, `yield`/`nothing`/`blocked`; Lerena's `searched.json` starts with a `_note` row; Lerena's corrections carry `date`/`what_was_said`.
* **Defranceschi, Blažević, D'Arcy**: `11 Nov 2026` or long month names; Blažević's corrections have no date (they stay on the corrections page; no correction cards).
* **Mazza**: `status` (done, found, part, outstanding) where others have `outcome`; `outcomeMap: { done: "found", part: "partial" }` after checking what `done` means in its log.
* **Falco**: `when` is the year of the record, not the day of the work, so almost nothing is dated; give it a work date first or leave the page to the corrections cards.
* **Booyzen**: `searched.json` is `{sets, searched}`; `rowsOf` reads `searched`.
