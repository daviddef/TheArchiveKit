/* A place a reader can take in, out of a place a tree exported.
 *
 * The same string keeps arriving in three broken shapes across this estate
 * and each one was being printed whole:
 *
 *   a gloss after a dash   Falco g3's bornPlace is "Arienzo — baptised in
 *                          the Collegiate Church of Sant'Andrea Apostolo"
 *   a repeated level       D'Arcy writes "Brisbane, Brisbane, Queensland,
 *                          Australia"; Blazevic writes "Senj, Croatia,
 *                          Senj, Općina Senj, Lika-Senj County, Croatia"
 *   a tree's own filler    D'Arcy prefixes a seat with "Of,"
 *
 * So: cut the gloss, drop any level that repeats one already kept — not
 * only the one before it, which is what let Blazevic's Senj through twice
 * — drop the filler, then keep whole comma levels while they fit.
 *
 * THE LEVELS THAT FALL OFF THE END ARE THE GENERAL ONES, which is the
 * right way round: "Darcy Meynill, Yorkshire" says more than "Yorkshire,
 * England", and "Brisbane, Queensland" more than "Queensland, Australia".
 * Nothing is corrected and nothing is added — this only decides how much
 * of what the archive holds will fit where it is being drawn.
 */
export function tidyPlace(raw, max = 30) {
  const parts = [];
  const seen = new Set();
  for (const seg of String(raw ?? "").split(/\s+[–—-]\s+/)[0].split(",")) {
    const t = seg.trim();
    if (!t || /^of$/i.test(t)) continue;
    const k = t.toLowerCase();
    if (seen.has(k)) continue;          // any earlier level, not just the last
    seen.add(k);
    parts.push(t);
  }
  let out = "";
  for (const t of parts) {
    const next = out ? out + ", " + t : t;
    if (next.length > max) break;
    out = next;
  }
  if (out) return out;
  const first = parts[0] || "";
  return first.length > max ? first.slice(0, max - 1).replace(/[\s,(]+$/, "") + "…" : first;
}

export default tidyPlace;
