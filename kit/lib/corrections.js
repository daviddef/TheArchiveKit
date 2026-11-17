/* corrections.js — what the Corrections page and /whats-new/ must agree on, so that a correction on What's new can link to THAT correction.
 *
 * Before this, a "Corrected" card on What's new linked to /corrections/ and nowhere else: the page has hundreds of entries and the reader had to
 * find theirs by eye. Both sides now compute the same anchor from the archive's own correction row (its date and its headline), so the link lands on
 * the entry. The archive does not choose or store ids: it passes its rows through corrIdMap() and puts the id on the entry it draws.
 *
 * Pure functions, no DOM, no locale: they run in the build and in node kit/tools/corrections_logic.mjs. */
import { parseWhen } from "./when.js";

/* the field names the eight archives use for a correction's date and headline (the same lists lib/pulse.js reads: cwhen, cwhat) */
const WHEN = ["when", "date"], WHAT = ["what", "what_was_said", "was"];
const first = (r, keys) => { for (const k of keys) if (r && r[k] != null && r[k] !== "") return r[k]; return ""; };

/* FNV-1a, 32 bit: no dependency, same answer in node and the browser */
const fnv = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h >>> 0; };
const norm = (s) => String(s == null ? "" : s).replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().slice(0, 240);

/* the anchor of each correction row: "c-2026-11-17-1k3f9a" (the day, then a hash of the headline). Two rows with the same day and headline get
   -2, -3 in the order given, so pass the rows in the archive's FILE order, not a sorted copy. Returns a Map from each row object to its id. */
export function corrIdMap(rows) {
  const map = new Map(), seen = new Map();
  for (const r of rows || []) {
    if (!r || typeof r !== "object") continue;
    const w = parseWhen(first(r, WHEN));
    const base = "c-" + (w ? w.iso : "undated") + "-" + fnv(norm(first(r, WHAT))).toString(36);
    const n = (seen.get(base) || 0) + 1; seen.set(base, n);
    map.set(r, n === 1 ? base : base + "-" + n);
  }
  return map;
}

/* newest first. A row whose date cannot be read (Mazza's undated rows, a record year) goes after the dated ones, in the order it came; rows on the
   same day keep the order they came in (the archive may put the serious ones first within a day). `whenOf` says where a row keeps its date. */
export function byDateDesc(rows, whenOf = (r) => r && r.when) {
  const keyed = (rows || []).map((r, i) => { const w = parseWhen(whenOf(r)); return { r, i, iso: w ? w.iso : "" }; });
  if (!keyed.some((k) => k.iso)) return [...(rows || [])];
  keyed.sort((a, b) => (a.iso === b.iso ? a.i - b.i : !a.iso ? 1 : !b.iso ? -1 : a.iso < b.iso ? 1 : -1));
  return keyed.map((k) => k.r);
}
