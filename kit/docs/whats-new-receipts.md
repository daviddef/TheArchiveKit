# What's new: "in the Atlas" and "page updated"

12 November 2026. David: "required for new found rows, both" (both = a build-time snapshot AND a view-time refresh).
Spec: `Working Folder/Research Menu Rollout/whats-new-atlas-and-pages-spec.md`. Nothing here is merged or deployed until David says; say
"added locally", "published" and "live" for what they are.

## What the reader sees

Under each search row on an archive's `/whats-new/`, one compact line with two parts:

1. **The Atlas state**, a small pill that says it in words (and in its outline, dashed or dotted, so colour is never the only signal):
   - **In the Atlas**: the row's receipt is in the Atlas's *deployed* receipts, with a link **"see it in the Atlas"** to the first Atlas page of the row's marks (the others, one link per page, under "and N more pages"). The receipts' hrefs are page paths (`/place/<place>/`, `/archive/<provider>/`, `/my-research/`), **no anchors**: the link reaches the page, not the volume's own row, and says so in its tooltip; it is not a deep-link claim.
   - **Sent, going live**: the receipt is in the Atlas repo's `main` but not yet deployed (the Atlas deploy takes 13 to 65 minutes).
   - **Not sent yet**: no receipt anywhere.
   - **Nothing to send**: the importer processed the row and it makes no mark (an empty list): a host or source the Atlas has no provider for, or a note with no source or volume. This is common (in the Defranceski run, 137 of 951 rows), is not a fault, and is not counted in the tally.
2. **Updated**: the archive's pages the finding went into, as links (the row's existing `ev`, `[[path, label], ...]`), or "log only" when the row says `"logOnly": true`. A row with neither shows no Updated line.

The day card's tally says "8 of 9 in the Atlas": of the rows that make a mark, those that are live. "Nothing to send" rows are not counted; a row whose state is
unknown is in neither figure; "going live" rows are counted in the 9 but not the 8.

The page says **"Record Atlas status as of 12 Nov 2026, when this page was built."** (the build-time snapshot). A small inline script then asks the Atlas again when the
page is opened, redraws the pills and tallies, and says **"Record Atlas status: checked just now."** If anything fails (offline, no CORS header, a missing file, bad JSON) it does
nothing and the build-time states stay. **Until the Atlas Worker with `Access-Control-Allow-Origin: *` on `/research-receipts/*` is deployed, the live fetch fails in every browser, so the page shows the build-time states "as of <date>" and never says "checked just now"**; `raw.githubusercontent.com` already allows any origin, but the refresh needs both files. `tools/receipts_logic.mjs` runs the script against a failing, a 404, a non-receipt, a broken-JSON and a never-answering fetch and asserts it changes and throws nothing.

## Where the states come from

One file per archive, written by the Atlas importer and committed by the Atlas publisher in the same commit as the marks:

```
https://recordatlas.org/research-receipts/<archive>.json                                          (deployed: "live")
https://raw.githubusercontent.com/daviddef/TheMap/main/site/public/research-receipts/<archive>.json  (the Atlas repo's main)
{ "v": 1, "exported": "2026-11-12",
  "rows": { "e7c29e4b77d3": [["volume:9R28-C6V", "/place/…#…"], ["source:familysearch", "/…"]],
            "afb2db3a6e3a": [] } }
```

A key with marks = the row made them; `[]` = processed, no mark; absent = not processed. Keys and Atlas paths only: no person's name, no row text.
`<archive>` is one of exactly these eight ids (`ARCHIVE_IDS` in `lib/receipts.js`, confirmed by the Atlas session, TheMap PR #15): **`blazevic`, `booyzen`, `darcy`, `defranceschi`, `falco`, `lerena`, `luwinski`, `mazza`**. Defranceski is `defranceschi`, with a c-h-i. `loadReceipts` with any other id warns and returns null; **`atlasId` is required to wire the page** and `WhatsNew` throws at build time if the page is wired with a missing or unknown one (a typo would otherwise read no receipts without a word). Not wired at all (no `receipts`, no `atlasId`) is still allowed and draws as before.

**Row identity**: `rowkey(row) = sha1(canonical_json(row))[:12]`, the row object exactly as it sits in `searched.json`, keys sorted at every level, no spaces, non-ASCII left
as it is (Python: `json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`). Editing a row changes its key, so an edited row reads "Not sent yet" until the
next publish: intended. Three test vectors (in the spec) are asserted in `tools/receipts_logic.mjs`, which also checks the JavaScript against Python on further rows.

**States** (`stateOf(key, live, main)`): deployed file has the key with marks, **in-atlas**; else main has it with marks, **going-live**; an empty list in either, **nothing-to-send**; in neither
and *both files were read*, **not-sent**; in neither and one file could not be read, **unknown** (`null`): a file that is down is not a "no". Every href is an Atlas path only
(another host, `//host` or `javascript:` is dropped).

## The parts

| piece | file |
|---|---|
| row key, `loadReceipts`, `stateOf` | `lib/receipts.js` |
| the view-time script (an inlined ES5 copy of `stateOf`) | `lib/receipts.client.js` |
| `key`, `atlas`, `updated` on each entry; `receipts` option; the day tally; `pulse.atlas` | `lib/pulse.js` |
| the two lines, the pill, the tally | `components/WhatsNewDay.astro`, `components/WhatsNew.astro` |
| the gate | `tools/check_row_pages.py` (selftest `check_row_pages_selftest.py`) |
| tests | `tools/receipts_logic.mjs` (in `npm test`) |

`buildPulse({ ..., receipts })`: `receipts` is what `loadReceipts` returns, `{ live, main, asOf }` (either file may be `null`), or `null`/absent: then no entry has an Atlas state and
nothing else changes. Each search entry carries `key`, `atlas` (`{ state, href, marks }` or `null`) and `updated` (`{ pages: [[path, label]], logOnly }`); each day carries `atlas`
(`{ in, going, notSent, nothing, makes }`) and `atlasTally` (`" · 8 of 9 in the Atlas"` or `""`).

`<WhatsNew atlasId="defranceschi" />`: with `atlasId` (or when the pulse carries receipts; then `atlasId` is required) the page draws the two lines; without both it is drawn exactly as before. `atlasId` is also what the
view-time refresh uses to find the two files. `liveUrl` / `mainUrl` override the addresses (a demo with sample receipts does; no archive should).

`loadReceipts(id, { fetch, timeout, now })` runs at build time, with a timeout of 8 seconds per file, and **never throws and never fails a build**: any failure gives `null` (or `null` for the one file that failed).
A build with the Atlas unreachable simply has no build-time Atlas line, and the view-time refresh can still fill them in.

## Wiring an archive in (one PR per archive, with the pin bump)

0. The Atlas side must exist first: the receipt files for the archive's id, deployed and on `main`, and the CORS header deployed for the view-time refresh.
1. **`src/lib/pulse.js`** (the adapter; the ribbon and `/whats-new/` share it, so the files are read once per build):

```js
import { buildPulse } from "@daviddef/archive-kit/lib/pulse.js";
import { loadReceipts } from "@daviddef/archive-kit/lib/receipts.js";
export const pulse = buildPulse({
  searched, corrections, worklist, counts: { ... },
  receipts: await loadReceipts("defranceschi"),       // the archive's id in the Atlas; null on any failure, never throws
});
```

2. **`src/pages/whats-new.astro`**: `<WhatsNew pulse={pulse} atlasId="defranceschi" ... />` (the Atlas's id for this archive, from the list above; required).
3. **`docs/row-pages.json`**: `{"from": "YYYY-MM-DD"}`, the day the gate starts (rows before it are not checked). Absent = gate off.
4. **`package.json`**: add `"check:row-pages": "python3 node_modules/@daviddef/archive-kit/kit/tools/check_row_pages.py --dist dist"` and run it after `astro build` in `build`.
   (It reads `src/data/searched.json` and `src/data/corrections.json`, and `docs/row-pages.json` or `../docs/row-pages.json`; `--searched`, `--corrections`, `--config` override.)
5. Nothing else: no CSS, no layout change. An archive that does none of this renders as before.

## The gate (`check_row_pages.py`)

From the date in `docs/row-pages.json`, every `searched.json` row whose outcome reads as **found** must have `ev` with at least one path that is a **built page** (`dist/<path>/index.html`; an anchor
or query is ignored), **or** `"logOnly": true` (the reason goes in `what`). "Found" is decided exactly as `lib/pulse.js` decides it: the same outcome words (`hit`, `yield`, `found`), the
same field names (`when`/`date`, `outcome`/`status`), the same dates (`2026-11-11`, `11 Nov 2026`, `Sept 2026`); a row pulse.js cannot date is not on `/whats-new/` and is not checked;
`receipts_logic.mjs` runs the Python and the JavaScript on the same words and dates. An archive's own outcome word is taught with `"outcomeMap": {"done": "found"}` in `docs/row-pages.json`
(the same as `buildPulse`'s `outcomeMap`). A misspelt date in the config **fails**: a typo must not turn the gate off.

Advisory only: a correction dated from the same day whose `where` names a path that is not a built page is a **warning**, not a failure.

Without `--dist` only the shape of the paths is checked, and it says so.
