/* THE BOOK: the whole site read as one book, woven on a spine (David, 17 October 2026).
 *
 * Seven menus group an archive's pages by KIND (Start, Our line, The families, ...). A book groups them
 * by the STORY: where they came from, the four grandparents, the crossing, how the lines join, everyone,
 * how we know. Every page of the site is one chapter, in one order, and every page says where it sits and
 * what comes next. Nothing moves and no address changes: the menus stay as shortcuts.
 *
 * Each archive keeps ONE file, site/src/data/book.json:
 *
 *   { "title": "The Mazza Archive",
 *     "front": { "label": "Front matter", "intro": "", "chapters": [ { "path": "/", "title": "The cover", "blurb": "" } ] },
 *     "parts": [ { "id": "where-from", "numeral": "I", "title": "Three towns on a strait", "intro": "…",
 *                  "flags": "🇮🇹", "chapters": [ { "path": "/atlas/", "title": "The Atlas", "blurb": "…", "group": "optional sub-heading" } ] } ],
 *     "inherit": { "/people/": "/people/", "/who/": "/who/" },     person and name pages belong to the chapter of their index
 *     "outside": [ "/search/" ] }                                   pages that are deliberately not chapters
 *
 * The book's order is: front matter, then for each part its OPENER (/part/<id>/, generated) and its chapters.
 * Previous / Next follow that order across the whole site. A page that is not in `chapters`, `inherit` or
 * `outside` fails the build (kit/tools/checkbook.py).
 *
 * Every page has a REFERENCE: front matter F.1, F.2 ...; a part opener is its numeral (I, II ...); a chapter is its part's
 * numeral and its place in that part (I.1, I.2 ... II.1 ...). Groups (sub-headings) do not take numbers. The reference is
 * what the running head, the foot and the Contents print, so a chapter can be cited by it.
 *
 * Pure functions: no imports, so the Python checker and this file are held to the same cases
 * (kit/data/book-cases.json) and cannot drift apart.
 */

export const PART_HUES = ["#d9776a", "#e0a85a", "#8fb4c9", "#8fc9a0", "#b49be0", "#c9a58f", "#9aa7b4", "#e08fb4", "#a3c97a"];

export function norm(p) {
  let s = String(p ?? "/").split("#")[0].split("?")[0];
  if (!s.startsWith("/")) s = "/" + s;
  if (!s.endsWith("/") && !/\.[a-z0-9]+$/i.test(s)) s += "/";
  return s;
}

export const openerPath = (part) => `/part/${part.id}/`;

/* The linear order: [{ path, title, blurb, kind: "front"|"opener"|"chapter", part: index|null, group }] */
export function flatten(book) {
  const out = [];
  ((book.front && book.front.chapters) || []).forEach((c, k) => {
    out.push({ path: norm(c.path), title: c.title, blurb: c.blurb || "", kind: "front", part: null, group: c.group || "", ref: `F.${k + 1}` });
  });
  (book.parts || []).forEach((part, i) => {
    const num = part.numeral || String(i + 1);
    out.push({ path: openerPath(part), title: part.title, blurb: part.intro || "", kind: "opener", part: i, group: "", ref: num });
    (part.chapters || []).forEach((c, k) => {
      out.push({ path: norm(c.path), title: c.title, blurb: c.blurb || "", kind: "chapter", part: i, group: c.group || "", ref: `${num}.${k + 1}` });
    });
  });
  return out;
}

/* Where is `path` in the book?
 *   { entry, index, n, total, prev, next, part, inherited:false }   a chapter, an opener or front matter
 *   { entry, index, n, total, prev:null, next:null, part, inherited:true, via }   a page that belongs to a chapter by prefix
 *   { outside:true }                                                 deliberately outside
 *   null                                                              nowhere: the build must fail on it */
export function locate(book, path) {
  const p = norm(path);
  const entries = flatten(book);
  const total = entries.length;
  const i = entries.findIndex((e) => e.path === p);
  const partOf = (e) => (e.part == null ? null : book.parts[e.part]);
  if (i >= 0) {
    const e = entries[i];
    return { entry: e, index: i, n: i + 1, total, prev: entries[i - 1] || null, next: entries[i + 1] || null, part: partOf(e), inherited: false };
  }
  if (p === "/contents/") return { outside: true };   /* the Contents page is the book's own table: it needs no chapter */
  /* `outside` is read BEFORE `inherit`: a page listed as outside stays outside even under an inherited prefix */
  if ((book.outside || []).map(norm).includes(p)) return { outside: true };
  const inh = book.inherit || {};
  const prefixes = Object.keys(inh).map(norm).sort((a, b) => b.length - a.length);
  for (const pre of prefixes) {
    if (p.startsWith(pre) && p !== pre) {
      const target = norm(inh[Object.keys(inh).find((k) => norm(k) === pre)]);
      const j = entries.findIndex((e) => e.path === target);
      if (j >= 0) {
        const e = entries[j];
        return { entry: e, index: j, n: j + 1, total, prev: null, next: null, part: partOf(e), inherited: true, via: pre };
      }
    }
  }
  return null;
}

/* Every page the book says it contains, for the coverage check and the Contents page. */
export function chapterPaths(book) { return flatten(book).filter((e) => e.kind !== "opener").map((e) => e.path); }
