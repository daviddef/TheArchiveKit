/* booklinks.js — link a register BOOK named in prose to the book itself.
 *
 * "The Svetvinčenat baptism book 1764–1791" was plain text: the linking standard links people and cited records, and nothing linked a book, though the
 * archive's own catalogue lists that volume with its FamilySearch image. This reads such a phrase out of the sentences and links it to the volume the
 * catalogue lists, and ONLY when the catalogue answers it: the same parish, the same kind of book (a baptism book is a Births volume, a burial or death
 * book a Deaths volume, a marriage or wedding book a Marriages volume), and years that fall inside the volume's years. A phrase that matches no volume,
 * or two different volumes, is left as written. Nothing is guessed; no link is made that the catalogue does not hold.
 *
 * The archive supplies its catalogue as plain rows; the kit does not know any archive's files:
 *   bookIndex([{ parish: "Svetvinčenat", label: "Births (Rođeni) 1764-1791, 1815-1874", href: "https://www.familysearch.org/ark:/61903/3:1:…" }, …])
 *   linkBooks(html, index)  →  html with <a class="lk-book" …> around each matched phrase (text outside links and code only)
 * Pure functions, no DOM: they run in the build and in node kit/tools/corrections_logic.mjs. */

const fold = (s) => String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const attr = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

/* what kind of book a volume's label (Croatian church books: "Births (Rođeni) 1584-1608", "Deaths (Umrli)…", "Marriages (Vjenčani)…") or a phrase's word is */
const KINDS = [["birth", /^(?:births?|born|rodjeni|baptism\w*|baptis\w*|krsteni)\b/], ["death", /^(?:deaths?|burials?|umrli)\b/], ["marriage", /^(?:marriages?|vjencani|weddings?)\b/]];
export function bookKind(word) { const t = fold(word).trim(); for (const [k, re] of KINDS) if (re.test(t)) return k; return ""; }

/* every year range in a label: "1764-1791, 1815-1874" → [[1764,1791],[1815,1874]]; a single year is a range of one */
export function bookYears(label) {
  const out = [], t = String(label || "").replace(/\([^)]*\)/g, " ");
  for (const m of t.matchAll(/\b(\d{4})(?:\s*[-–]\s*(\d{4}))?\b/g)) out.push([+m[1], +(m[2] || m[1])]);
  return out;
}

export function bookIndex(rows) {
  const vols = [];
  for (const r of rows || []) {
    const parish = String((r && r.parish) || "").trim(), href = String((r && r.href) || "").trim(), kind = bookKind(r && r.label), ranges = bookYears(r && r.label);
    if (!parish || !href || !kind || !ranges.length) continue;
    vols.push({ parish, key: fold(parish), kind, ranges, href, label: String(r.label) });
  }
  const parishes = [...new Set(vols.map((v) => v.parish))].sort((a, b) => b.length - a.length);
  const names = [...new Set(parishes.flatMap((p) => [p, p.normalize("NFD").replace(/[̀-ͯ]/g, "")]))].sort((a, b) => b.length - a.length);
  const re = names.length ? new RegExp("(?<![\\p{L}\\d])(" + names.map(esc).join("|") + ")\\s+(baptism|baptismal|baptisms|birth|death|burial|marriage|wedding)s?\\s+(?:book|books|register|registers)\\s+(\\d{4})(?:\\s*[–-]\\s*(\\d{4}))?", "giu") : null;
  return { vols, re };
}

/* the volume a phrase names: same parish, same kind, the phrase's years inside one of the volume's ranges; one answer or none */
function volumeFor(index, parish, word, from, to) {
  const kind = bookKind(word), key = fold(parish);
  const hit = index.vols.filter((v) => v.key === key && v.kind === kind && v.ranges.some(([a, b]) => from >= a && to <= b));
  const hrefs = [...new Set(hit.map((v) => v.href))];
  return hrefs.length === 1 ? hit[0] : null;
}

export function linkBooks(html, index) {
  if (!html || !index || !index.re) return html;
  let depth = 0;
  return String(html).split(/(<[^>]*>)/).map((tok) => {
    if (tok.startsWith("<")) {
      if (/^<(?:a|code|pre|script|style)\b/i.test(tok)) depth++;
      else if (/^<\/(?:a|code|pre|script|style)\s*>/i.test(tok)) depth = Math.max(0, depth - 1);
      return tok;
    }
    if (depth > 0 || !tok) return tok;
    return tok.replace(index.re, (all, parish, word, y1, y2) => {
      const from = +y1, to = +(y2 || y1);
      if (to < from) return all;
      const v = volumeFor(index, parish, word, from, to);
      return v ? `<a class="lk-book" href="${attr(v.href)}" rel="noopener" title="${attr("FamilySearch: " + v.parish + ", " + v.label)}">${all}</a>` : all;
    });
  }).join("");
}
