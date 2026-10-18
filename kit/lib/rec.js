/* The pure half of components/Rec.astro: what a record link is, worked out from the archive's records table.

   Nothing here knows an archive. The archive supplies a table of the records its prose cites; this decides, for one
   <Rec id="..."/> or <Rec act="63/1888"/>, what to draw: a link, a link and a small figure, or nothing.

   THE RECORDS TABLE (JSON: an array of rows, or {"records": [...]}), one row per record a passage may cite
     id      string, unique. What <Rec id="..."/> names, and what the link carries in data-rec.
     url     where the record is: https://... (or http://), or a root-relative address of the archive's own ("/sources/x/").
             Nothing else is accepted (no javascript:, data:, protocol-relative or relative address). Required unless
             the row is flagged living or hold.
     label   a short human name for the record ("Register of marriages, 1888, act 63"). The link's tooltip, the
             figure's alt text, and the link's text when the author wrote none.
     kind    optional. What sort of record ("act", "ark", "census"...): carried as data-kind, for styling and counting.
     key     optional. The locator an author may cite it by instead of the id, a string or a list of strings
             ("63/1888"). Compared folded (case, accents, punctuation runs to one space), so "63/1888", "63-1888" and
             "63 / 1888" are one key. Two records may not share a key.
     plate   optional. A scan the archive holds of this record: a file name or path relative to the plates base ("x.jpg").
     show    true when the archive's own rules let it show that scan. Exactly true: any other value is "do not show".
     living  true when the record concerns a person who is or may be living; hold: true when the archive withholds it for
             any other reason. A row flagged either way is NEVER drawn: no link, no figure, no text, and no plate, whatever
             else the row says. (The archive's own gate decides what to flag; this only honours the flag.)

   WHAT IT DRAWS (describe): state "ok" with an address and, only when the author asked for a thumbnail (thumb), the row has
   a plate and show is true, the plate to draw; state "blocked" (draw nothing); or, for an id or locator the table does not
   hold, an error that stops the build (a link that is a guess is worse than no link), except with soft, which draws the
   author's own text unlinked.

   No import: this runs in node as it does in a build, so the kit can test it without Astro. */

export class RecError extends Error {}

/* A key as it is compared: the same folding the linking standard's gate gives a scan key (case, accents and apostrophes
   gone, every other run of punctuation and spaces one space). */
export function fold(s) {
  return String(s == null ? "" : s)
    .normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/['’`]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

const truthy = (v) => v === true || (v != null && v !== false && v !== 0 && v !== "" && v !== "0" && String(v).toLowerCase() !== "false");

/* A row the archive withholds: living or hold, in any spelling of "yes". Fail closed: a flag that is anything but an
   unmistakable "no" blocks. */
export function isBlocked(row) {
  return !!row && (truthy(row.living) || truthy(row.hold));
}

/* An address a link may carry, or null. https/http, or root-relative ("/x"), never "//host", never a scheme like
   javascript:, never a relative address, never whitespace or control characters. */
export function safeHref(url) {
  if (typeof url !== "string") return null;
  const s = url.trim();
  if (!s || /[\s\u0000-\u001f\u007f<>"]/u.test(s)) return null;
  if (/^https?:\/\/[^/?#\s]+/i.test(s)) return s;
  if (s.startsWith("/") && !s.startsWith("//") && !s.includes("\\")) return s;
  return null;
}

const PLATE = /^[\p{L}\p{N}_][\p{L}\p{N}_.\- ]*(?:\/[\p{L}\p{N}_][\p{L}\p{N}_.\- ]*)*$/u;
const safePlate = (p) => typeof p === "string" && PLATE.test(p) && !p.split("/").some((seg) => seg === ".." || seg === ".");

/* The table, read once: validated whole (a typo should stop the build when the table is read, not when the one page that
   cites it is built), with its two lookups. */
const cache = new WeakMap();
export function index(raw) {
  if (raw && typeof raw === "object" && cache.has(raw)) return cache.get(raw);
  const rows = Array.isArray(raw) ? raw : raw && Array.isArray(raw.records) ? raw.records : null;
  if (!rows) throw new RecError("the records table must be an array of rows, or {\"records\": [...]}");
  const byId = new Map(), byKey = new Map();
  rows.forEach((r, i) => {
    if (!r || typeof r !== "object" || typeof r.id !== "string" || !r.id.trim()) throw new RecError(`records row ${i}: no id`);
    if (byId.has(r.id)) throw new RecError(`records row ${i}: the id is used twice`);
    byId.set(r.id, r);
    if (!isBlocked(r)) {
      if (safeHref(r.url) === null) throw new RecError(`records row ${i}: url must be https://..., http://... or a root-relative address`);
      if (r.plate != null && r.plate !== "" && !safePlate(r.plate)) throw new RecError(`records row ${i}: plate must be a plain file name or path`);
    }
    for (const k of [].concat(r.key == null ? [] : r.key)) {
      const f = fold(k);
      if (!f) continue;
      if (byKey.has(f) && byKey.get(f) !== r) throw new RecError(`records row ${i}: a key is shared with another record`);
      byKey.set(f, r);
    }
  });
  const ix = { byId, byKey, size: rows.length };
  if (raw && typeof raw === "object") cache.set(raw, ix);
  return ix;
}

/* What to draw for one citation.
     props  { id } or { act }        opts  { thumb, soft, plateBase, root }
   `root` maps a root-relative address to the deployed one (the kit's u()); default: unchanged. */
export function describe(ix, props = {}, opts = {}) {
  const { id, act } = props;
  const { thumb = false, soft = false, plateBase = "/plates/", root = (p) => p } = opts;
  if ((id == null) === (act == null)) throw new RecError("<Rec> takes exactly one of id and act");
  const row = id != null ? ix.byId.get(String(id)) : ix.byKey.get(fold(act));
  if (!row) {
    if (soft) return { state: "plain" };
    throw new RecError(`<Rec ${id != null ? 'id="' + id + '"' : 'act="' + act + '"'}>: the records table has no such record`);
  }
  if (isBlocked(row)) return { state: "blocked" };
  const href = safeHref(row.url);
  if (href === null) throw new RecError(`<Rec id="${row.id}">: the record's url is not one a link may carry`);
  const mapped = href.startsWith("/") ? root(href) : href;
  const label = typeof row.label === "string" ? row.label : "";
  const d = {
    state: "ok", id: row.id, href: mapped, external: !href.startsWith("/"), kind: typeof row.kind === "string" ? row.kind : "",
    label, plate: null,
  };
  if (thumb && row.show === true && typeof row.plate === "string" && row.plate) {
    if (!safePlate(row.plate)) throw new RecError(`<Rec id="${row.id}">: the plate is not a plain file name`);
    const base = plateBase.endsWith("/") ? plateBase : plateBase + "/";
    const b = safeHref(base);
    if (b === null) throw new RecError("<Rec plateBase>: not an address a link may carry");
    const src = (b.startsWith("/") ? root(b) : b) + row.plate;
    const stem = row.plate.replace(/\.[A-Za-z0-9]{2,5}$/, "");
    d.plate = {
      src, full: src, alt: label || row.id, anchor: "plate-" + (fold(stem).replace(/ /g, "-") || "x"),
      w: Number.isInteger(row.w) && row.w > 0 ? row.w : null, h: Number.isInteger(row.h) && row.h > 0 ? row.h : null,
    };
  }
  return d;
}

/* One figure id per page render: the second <Rec> of a plate on the same page keeps its figure and gives up the id. The
   scope is any object that lives as long as one page render (Rec.astro passes Astro.request), so a dev server that renders
   the page again starts clean. */
const claimed = new WeakMap();
export function claim(scope, anchor) {
  if (!scope || typeof scope !== "object") return true;
  if (!claimed.has(scope)) claimed.set(scope, new Set());
  const s = claimed.get(scope);
  if (s.has(anchor)) return false;
  s.add(anchor);
  return true;
}

export const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/* The same markup Rec.astro draws, as a string, for the kit's tests and for any page that is not Astro. `text` is plain text
   (escaped here); empty text draws the record's label. A blocked record is the empty string. `anchor` false leaves the
   figure without its id. */
export function renderRec(d, text = "", anchor = true) {
  if (d.state === "blocked") return "";
  const t = esc(text);
  if (d.state === "plain") return t;
  const a = `<a class="lk-rec" href="${esc(d.href)}" data-rec="${esc(d.id)}" data-cite${d.kind ? ` data-kind="${esc(d.kind)}"` : ""}`
    + `${d.label ? ` title="${esc(d.label)}"` : ""}${d.external ? ' rel="noopener"' : ""}>${t || esc(d.label || d.id)}</a>`;
  if (!d.plate) return a;
  const p = d.plate;
  return `<figure class="rec-fig"${anchor ? ` id="${esc(p.anchor)}"` : ""}><a class="rec-fig-img" href="${esc(p.full)}">`
    + `<img src="${esc(p.src)}" alt="${esc(p.alt)}"${p.w ? ` width="${p.w}"` : ""}${p.h ? ` height="${p.h}"` : ""} loading="lazy" decoding="async"></a>`
    + `<figcaption>${a}</figcaption></figure>`;
}
