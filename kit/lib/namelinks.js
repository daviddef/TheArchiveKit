/* namelinks.js — link the NAMES in a correction's prose to their person page, or, where several people bear the name, to the list of them.
 *
 * The same index the archive already builds for kit/tools/autolink.py (kit/docs/autolink.md) is read here, so no archive writes a second one:
 *
 *   { "people":    [{ "name": "Given Family", "aliases": ["Family Given"], "url": "/people/given-family/" }],
 *     "ambiguous": [{ "name": "Given Family", "url": "/people/?q=Given%20Family" }] }
 *
 *   nameIndex(idx, { minWords: 2, avoid: ["Names that are living or held out"] })
 *   linkNames(html, index, { seen: new Set() })  →  html with <a class="lk-name" href data-autolink="person"> around the FIRST mention of each person
 *
 * A name borne by one person with a page links to that person. A name borne by several links to the archive's list of them (class lk-shared, and a
 * title that says several people share it), never to one of them: nobody is guessed. Text inside a link, code, a heading is left alone. A name that
 * overlaps one in `avoid` (a living person's name that contains a dead one's: the autolinker's living rule) is not linked there. `seen` is the set of
 * addresses already linked in this entry, so the same person is linked once however many fields name them. Pure functions, no DOM. */

const fold = (s) => String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const attr = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const BEFORE = "(?<![\\p{L}\\d'’-])", AFTER = "(?![\\p{L}\\d]|[-'’]\\p{L})";
export const SHARED_TITLE = "Several people share this name: opens the list";

function compile(names) {
  const list = [...new Set(names)].sort((a, b) => b.length - a.length || (a < b ? -1 : 1));
  return list.length ? new RegExp(BEFORE + "(" + list.map(esc).join("|") + ")" + AFTER, "giu") : null;
}

export function nameIndex(idx, o = {}) {
  const minWords = o.minWords == null ? 2 : o.minWords, byKey = new Map(), terms = [];
  const put = (name, url, shared) => {
    const t = String(name || "").trim(), u = String(url || "").trim();
    if (!t || !u || t.split(/\s+/).length < minWords) return;
    const k = fold(t), had = byKey.get(k);
    if (had && had.url !== u) { byKey.set(k, { url: "", shared: true, skip: true }); return; }   /* one name, two addresses: not linked */
    byKey.set(k, { url: u, shared: !!shared, text: t });
    terms.push(t, t.normalize("NFD").replace(/[̀-ͯ]/g, ""));
  };
  for (const p of (idx && idx.people) || []) { put(p.name, p.url, false); for (const a of p.aliases || []) put(a, p.url, false); }
  for (const a of (idx && idx.ambiguous) || []) put(a.name, a.url, true);
  return { byKey, re: compile(terms), avoid: compile((o.avoid || []).filter((x) => String(x || "").trim())), labels: Object.assign({ shared: SHARED_TITLE }, o.labels || {}) };
}

export function linkNames(html, index, o = {}) {
  if (!html || !index || !index.re) return html;
  const seen = o.seen || new Set();
  let depth = 0;
  return String(html).split(/(<[^>]*>)/).map((tok) => {
    if (tok.startsWith("<")) {
      if (/^<(?:a|code|pre|script|style|h[1-6]|svg|button|select|textarea)\b/i.test(tok)) depth++;
      else if (/^<\/(?:a|code|pre|script|style|h[1-6]|svg|button|select|textarea)\s*>/i.test(tok)) depth = Math.max(0, depth - 1);
      return tok;
    }
    if (depth > 0 || !tok) return tok;
    const hold = [];
    if (index.avoid) for (const m of tok.matchAll(index.avoid)) hold.push([m.index, m.index + m[0].length]);
    return tok.replace(index.re, (all, name, at) => {
      const e = index.byKey.get(fold(name));
      if (!e || e.skip || !e.url || seen.has(e.url)) return all;
      if (hold.some(([a, b]) => at < b && at + all.length > a)) return all;   /* overlaps a living or held-out name: not linked */
      seen.add(e.url);
      return e.shared
        ? `<a class="lk-name lk-shared" href="${attr(e.url)}" data-autolink="search" title="${attr(index.labels.shared)}">${all}</a>`
        : `<a class="lk-name" href="${attr(e.url)}" data-autolink="person">${all}</a>`;
    });
  }).join("");
}
