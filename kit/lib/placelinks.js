/* placelinks.js — link a PLACE named in prose to its place page, with the flag that flew over it.
 *
 * "Crikvenica" in a correction was plain text although the archive has /places/crikvenica/, and no flag showed. This reads the places the archive
 * lists out of the sentences and links each (the first mention in an entry) to its page. A place the archive has no page for is left as written.
 *
 * THE FLAG is the one the ribbon cards use (kit/docs/ribbon-flags.md): the state that held the place in the year the sentence is about, and, only
 * where it is another country's flag, today's. kit/tools/placeflags.py works both out for each place from the archive's era snapshot and the kit's
 * regime table and writes them as a table; this file only looks the year up. Nothing is guessed here either:
 *   - the year is the one year the sentence names; a sentence with two or more different years, or none, gets today's flag only;
 *   - a year of 2020 or later is the day the correction was made, not the day of the event, and is not read;
 *   - a place the table cannot give a flag for gets the link and no flag.
 *
 *   placeIndex([{ name, aliases?, href, flagKey? }], flags, flagUrl)   flags: the placeflags.py table { key: { today, eras } }; flagUrl(svgFile) → address or ""
 *   linkPlaces(html, index, { seen })  →  html with <a class="lk-place" href> (and <img class="pl-flag">) around the first mention of each place
 *
 * Pure functions, no DOM: they run in the build and in node kit/tools/corrections_logic.mjs. */

const fold = (s) => String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const attr = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const BEFORE = "(?<![\\p{L}\\d'’-])", AFTER = "(?![\\p{L}\\d]|[-'’]\\p{L})";
const country = (svg) => String(svg || "").split("--")[0];

export function placeIndex(rows, flags, flagUrl) {
  const byName = new Map(), names = [];
  for (const r of rows || []) {
    const href = String((r && r.href) || "").trim(), main = String((r && r.name) || "").trim();
    if (!href || !main) continue;
    const row = { name: main, href, key: (r && r.flagKey) || main };
    for (const n of [main, ...((r && r.aliases) || [])]) {
      const t = String(n || "").trim();
      if (t.length < 3 || !/^\p{Lu}/u.test(t)) continue;     /* a place is written with a capital; "rab" is not Rab, and nothing shorter than three letters is read */
      const had = byName.get(t);
      if (had && had.href !== href) { byName.set(t, { skip: true }); continue; }
      byName.set(t, row); names.push(t);
    }
  }
  const list = [...new Set(names)].sort((a, b) => b.length - a.length || (a < b ? -1 : 1));
  const re = list.length ? new RegExp(BEFORE + "(" + list.map(esc).join("|") + ")" + AFTER, "gu") : null;
  return { byName, re, flags: flags || {}, flagUrl: typeof flagUrl === "function" ? flagUrl : () => "" };
}

/* the one year a sentence names, or 0: the sentence around the match (up to the nearest . ; or newline each side) must name exactly one distinct year 1000-2019 */
export function yearAround(text, at, len) {
  let a = at, b = at + len;
  while (a > 0 && !/[.;\n]/.test(text[a - 1])) a--;
  while (b < text.length && !/[.;\n]/.test(text[b])) b++;
  const years = new Set();
  for (const m of text.slice(a, b).matchAll(/(?<!\d)(1[0-9]{3}|20[01][0-9])(?!\d)/g)) years.add(+m[1]);
  return years.size === 1 ? [...years][0] : 0;
}

/* the flags for a place in a year: [{svg, label}] — the era flag (if the year is known and the table has one), then today's where it is another country's */
export function flagsFor(index, key, year) {
  const t = index.flags[key];
  if (!t) return [];
  const out = [];
  let era = null;
  if (year && Array.isArray(t.eras)) era = t.eras.find((e) => year >= e[0] && year < e[1]) || null;
  if (era) out.push({ svg: era[2], label: era[3] + " then", era: true });
  const today = t.today && t.today.svg ? t.today : null;
  if (today && !(era && country(era[2]) === country(today.svg))) out.push({ svg: today.svg, label: today.label + " today" });
  return out;
}

export function linkPlaces(html, index, o = {}) {
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
    const plain = tok.replace(/&amp;/g, "&");
    return tok.replace(index.re, (all, name, at) => {
      const p = index.byName.get(name);
      if (!p || p.skip || seen.has(p.href)) return all;
      seen.add(p.href);
      const year = yearAround(plain, at, all.length), fl = flagsFor(index, p.key, year);
      const imgs = fl.map((f) => { const src = index.flagUrl(f.svg); return src ? `<img class="pl-flag" src="${attr(src)}" alt="" width="18" height="12" loading="lazy">` : ""; }).join("");
      const shown = fl.filter((f) => index.flagUrl(f.svg));
      const title = shown.length ? `${p.name}${shown[0].era ? ", " + year : ""}: ${shown.map((f) => f.label).join("; ")}` : p.name;
      return `<a class="lk-place" href="${attr(p.href)}" title="${attr(title)}">${imgs}${all}</a>`;
    });
  }).join("");
}
