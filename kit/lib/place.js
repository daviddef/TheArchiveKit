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


/* A LIVING PERSON'S PLACE IS A COUNTRY AND NOTHING FINER.
 *
 * Found on 22 September 2026: Mazza's published person pages carried a
 * birthplace for 256 living people, including a seven-year-old and a
 * nine-year-old whose pages read «Born  Brisbane, Queensland  withheld».
 * The date was withheld and the town was not.
 *
 * The estate's rule is a name and a relationship and nothing else. David's
 * decision was to keep a country: «can you just show country for the
 * living?» — enough to say a family ended up in Australia rather than
 * Italy, not enough to put a child in a town.
 *
 * EXPLICIT AND AUDITABLE, NOT INFERRED. The thirty-three places the estate
 * actually holds against a living person were listed before this was
 * written, and every region below appears in that list. A place that
 * resolves to nothing returns "" and the page shows no place at all —
 * never a guess, and never the town it was trying to avoid.
 */
const COUNTRY = "australia|italy|argentina|uruguay|brazil|croatia|germany|austria|" +
  "england|scotland|wales|ireland|france|spain|portugal|greece|indonesia|fiji|" +
  "south africa|new zealand|canada|mexico|switzerland|slovenia|serbia|hungary|" +
  "netherlands|belgium|poland|mozambique";

/* Region, state or province -> the country it is in. Only what this estate
   writes against a living person, so every line can be checked against a
   real record rather than trusted as general knowledge. */
const REGION = {
  // Australia
  queensland: "Australia", "new south wales": "Australia", victoria: "Australia",
  "western australia": "Australia", "south australia": "Australia",
  tasmania: "Australia", "northern territory": "Australia", vic: "Australia",
  // Italy
  sicily: "Italy", sicilia: "Italy", calabria: "Italy", catania: "Italy",
  "reggio calabria": "Italy", "reggio di calabria": "Italy", catanzaro: "Italy",
  "vibo valentia": "Italy", lombardy: "Italy", lombardia: "Italy",
  veneto: "Italy", benevento: "Italy", cosenza: "Italy", campania: "Italy",
  // elsewhere
  "new york": "United States", usa: "United States", "united states": "United States",
  "great britain": "Great Britain", uk: "Great Britain",
  "united kingdom": "Great Britain",
};

const COUNTRY_RE = new RegExp("^(?:" + COUNTRY + ")$", "i");

export function countryOnly(raw) {
  const parts = String(raw ?? "")
    .split(/\s+[\u2013\u2014-]\s+/)[0]
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  if (!parts.length) return "";

  // A country already written down wins, wherever it sits.
  for (let i = parts.length - 1; i >= 0; i--) {
    if (COUNTRY_RE.test(parts[i])) {
      return parts[i].replace(/\b\w/g, (c) => c.toUpperCase());
    }
  }
  // Otherwise the most specific region that is mapped. Last segment first,
  // because "Scilla, Reggio Calabria" names the region after the town.
  for (let i = parts.length - 1; i >= 0; i--) {
    const k = parts[i].toLowerCase().replace(/\s*\([^)]*\)/g, "").trim();
    if (REGION[k]) return REGION[k];
    // "Parkville Vic Australia" and the like: try the words too.
    for (const w of [k, ...k.split(/\s+/)]) if (REGION[w]) return REGION[w];
  }
  return "";
}
