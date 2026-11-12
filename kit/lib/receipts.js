/* RESEARCH RECEIPTS: has a row of the search log reached the Record Atlas? (kit lib, 12 November 2026; spec: "What's new: in the Atlas and
 * page updated", Research Menu Rollout).
 *
 * The Atlas importer writes one file per archive, keyed by the row's identity, at
 *     https://recordatlas.org/research-receipts/<archive>.json            (what is deployed: "live")
 *     https://raw.githubusercontent.com/daviddef/TheMap/main/site/public/research-receipts/<archive>.json   (the Atlas repo's main)
 *   { "v": 1, "exported": "2026-11-12", "rows": { "<rowkey>": [[markKey, href], ...], "<rowkey>": [] } }
 * A key with marks = the row made those marks; a key with [] = processed, makes no mark; a key absent = not processed.
 * No person's name and no row text is in a receipt: keys and Atlas paths only.
 *
 * Three pure pieces, no archive data:
 *   rowkey(row)                      the row's identity: sha1 of its canonical JSON, first 12 hex. THE SAME DEFINITION in the Atlas importer (Python);
 *                                    three test vectors in kit/tools/receipts_logic.mjs keep the two in step.
 *   loadReceipts(archiveId, opts)    BUILD time: fetch live and main. ANY failure returns null (or null for the one that failed); it can never fail a build.
 *   stateOf(key, live, main)         one of in-atlas / going-live / not-sent / nothing-to-send, plus the first Atlas path and all the marks.
 * The view-time script (receipts.client.js, inlined by WhatsNew.astro) carries a copy of stateOf; receipts_logic.mjs holds the two to identical answers.
 */
import { createHash } from "node:crypto";

export const LIVE_URL = (id) => `https://recordatlas.org/research-receipts/${id}.json`;
export const MAIN_URL = (id) => `https://raw.githubusercontent.com/daviddef/TheMap/main/site/public/research-receipts/${id}.json`;
export const ATLAS_ORIGIN = "https://recordatlas.org";

/* canonical JSON: keys sorted at every level, no spaces, non-ASCII left as it is (Python: json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",",":"))) */
export function canonical(v) {
  if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
  if (v && typeof v === "object") return "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ":" + canonical(v[k])).join(",") + "}";
  return JSON.stringify(v === undefined ? null : v);
}
/* Object.keys().sort() orders by UTF-16 code unit, Python's sort_keys by code point: the same for every key the archives use (all BMP); an astral-plane key is the one case they could differ */
export const rowkey = (row) => createHash("sha1").update(canonical(row), "utf8").digest("hex").slice(0, 12);

export const STATES = ["in-atlas", "going-live", "not-sent", "nothing-to-send"];
export const STATE_LABEL = {
  "in-atlas": "In the Atlas",
  "going-live": "Sent, going live",
  "not-sent": "Not sent yet",
  "nothing-to-send": "Nothing to send",
};

/* an Atlas path only: "/place/x/#y" becomes https://recordatlas.org/place/x/#y; anything else (another host, "//host", a script) is dropped */
export const atlasHref = (h) => {
  if (typeof h !== "string") return "";
  const t = h.trim();
  if (/^\/(?!\/)[^\s]*$/.test(t)) return ATLAS_ORIGIN + t;
  if (t.startsWith(ATLAS_ORIGIN + "/") && !/\s/.test(t)) return t;
  return "";
};
const hasRows = (x) => !!x && typeof x === "object" && x.rows && typeof x.rows === "object" && !Array.isArray(x.rows);
const marksOf = (list) => (Array.isArray(list) ? list : []).filter((m) => Array.isArray(m) && typeof m[0] === "string" && atlasHref(m[1])).map((m) => [m[0], atlasHref(m[1])]);
const has = (rows, key) => Object.prototype.hasOwnProperty.call(rows, key);

/**
 * stateOf(key, live, main) -> { state, href, marks } | null
 *   live / main: a parsed receipt file ({v, rows}) or null when that file could not be read.
 *   in-atlas         the key is in the DEPLOYED file with marks
 *   going-live       not deployed, but in the Atlas repo's main with marks
 *   nothing-to-send  the key is in a file with an empty list (processed, no mark)
 *   not-sent         the key is in neither file, and BOTH files were read
 *   null             cannot tell: the key is in neither file read and one of the two could not be read (a missing file is not a "no")
 * href is the first Atlas page (absolute, https://recordatlas.org/...) and marks every [markKey, href]; both empty unless the state has marks.
 */
export function stateOf(key, live, main) {
  const L = hasRows(live) ? live.rows : null, M = hasRows(main) ? main.rows : null;
  const done = (state, list) => { const marks = state === "nothing-to-send" || state === "not-sent" ? [] : marksOf(list); return { state, href: marks.length ? marks[0][1] : "", marks }; };
  if (L && has(L, key)) { const m = marksOf(L[key]); return m.length ? done("in-atlas", L[key]) : done("nothing-to-send"); }
  if (M && has(M, key)) { const m = marksOf(M[key]); return m.length ? done("going-live", M[key]) : done("nothing-to-send"); }
  if (L && M) return done("not-sent");
  return null;
}

const getJSON = async (fetchFn, url, ms) => {
  let timer = null;
  try {
    const ctl = typeof AbortController === "function" ? new AbortController() : null;
    /* the timeout is a race, not only an abort: a fetch that ignores its signal must not hold a build */
    const late = new Promise((_, no) => { timer = setTimeout(() => { if (ctl) ctl.abort(); no(new Error("timeout")); }, ms); });
    const get = (async () => {
      const r = await fetchFn(url, ctl ? { signal: ctl.signal } : undefined);
      if (!r || !r.ok) return null;
      const j = await r.json();
      return hasRows(j) && (j.v === undefined || j.v === 1) ? j : null;
    })();
    get.catch(() => {});
    return await Promise.race([get, late]);
  } catch (e) { return null; } finally { if (timer) clearTimeout(timer); }
};

/**
 * loadReceipts(archiveId, { fetch, timeout, now }) -> { live, main, asOf } | null      (BUILD time; never throws)
 *   fetch: defaults to the global fetch; a test or a demo passes its own (it receives the URL and must return a Response-like {ok, json()})
 *   timeout: milliseconds per file, default 8000
 *   asOf: today's date, YYYY-MM-DD, the day this snapshot was taken (the page says "as of <date>")
 * Returns null when neither file could be read. One file read and the other not gives { live: null, main: {...} } or the reverse: stateOf then
 * says only what it can know.
 */
export async function loadReceipts(archiveId, o = {}) {
  try {
    if (!archiveId || !/^[a-z0-9-]+$/i.test(String(archiveId))) return null;
    const f = o.fetch || (typeof fetch === "function" ? fetch : null);
    if (!f) return null;
    const ms = o.timeout || 8000;
    const [live, main] = await Promise.all([getJSON(f, LIVE_URL(archiveId), ms), getJSON(f, MAIN_URL(archiveId), ms)]);
    if (!live && !main) return null;
    return { live, main, asOf: (o.now ? new Date(o.now) : new Date()).toISOString().slice(0, 10) };
  } catch (e) { return null; }
}
