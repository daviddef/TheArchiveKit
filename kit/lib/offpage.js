/* Where a marriage leads — the off-page connectors on a spine row.
 *
 * Asked for on 22 September: «could you visually show the off page
 * connector in these lines to the "families"? … so we actually get to
 * navigate along the spine to the interlinked familiies?»
 *
 * A spine is a column of couples, and every wife on it is a door into
 * another family. Blazevic's generation two married a Papić and generation
 * three a Žubrinić, and this archive keeps a page on each of those
 * surnames — but the only way to reach them was a dropdown in the nav. The
 * spine, which is the page that actually shows the marriage, offered
 * nothing. And generation one married OUT of the estate's Croatian archive
 * into its Istrian one, which is a whole other site and was not linked at
 * all.
 *
 * So two kinds of door, and the difference matters to a reader:
 *
 *   in this archive   a surname this site keeps its own page on
 *   another archive   a surname the ring says belongs to a sibling site
 *
 * MATCHED ON A SURNAME, WHICH IS NOT AN IDENTITY — and that is fine here,
 * and is NOT fine for the person links elsewhere on the same row. A family
 * page is about everyone of a name; landing on Papić because the wife is
 * called Papić is correct even if two women share the name. A PERSON link
 * built the same way would merge them. Hence: families by name, people by
 * identifier, and never the reverse.
 *
 *   surnameDoors(name, { own, families, ring })
 *     name      the spouse as the archive writes her, e.g.
 *               "Milka Lucia Papic", "Cheryl Anne Defranceski, née Lerena"
 *     own       this archive's key in the ring, so it never links to itself
 *     families  [{ label, href, surnames? }] this site's own family pages;
 *               matched on `surnames` when given, otherwise on `label`
 *     ring      archives.json
 *   → [{ label, href, external }]  at most one of each kind, nearest first
 */

const fold = (s) =>
  String(s ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    // đ and ć/č survive NFD in some inputs; ß and ø have no decomposition
    .replace(/đ/gi, "d").replace(/ø/gi, "o").replace(/ß/gi, "ss")
    .toLowerCase()
    .replace(/[^a-z\s]/g, " ")
    .trim();

/* "Cheryl Anne Defranceski, née Lerena" is two surnames and the second is
   the one a reader wants a door to. Quotes, nicknames and the née/born/
   r./rođ. markers are dropped, and what is left is every word, because a
   surname can sit anywhere in these names — "Tereza Žubrinić Zubrinic"
   and "Milka Lucia Papic" put it in different places. */
/* A MAIDEN NAME IS THE DOOR THE READER WANTS. "Cheryl Anne Defranceski,
   née Lerena" carries two real surnames: the one she married into, which
   is the archive this row already sits in or beside, and the one she came
   from, which is the family this row is actually a join to. */
const maidenPart = (name) => {
  const parts = String(name ?? "").split(/\b(?:n[\u00e9e]e|born|rod|ro\u0111\.?|r\.)\s+/i);
  return parts.length > 1 ? parts[parts.length - 1] : "";
};

const STOP = new Set(["nee", "born", "rod", "rodj", "the", "von", "van", "de", "der", "di", "du"]);

/* Quotes and nicknames out; what is left is the folded name as a single
   spaced string, because a surname can sit anywhere in these — "Tereza
   Žubrinić Zubrinic" and "Milka Lucia Papic" put it in different places. */
const text = (name) => " " + fold(String(name ?? "").replace(/[""'']/g, " ")) + " ";

/* A SURNAME IS NOT ALWAYS ONE WORD. The first version folded each side to
   single tokens and asked whether a token set contained the needle — which
   can never be true for "D'Arcy", because folding strips the apostrophe
   and leaves the two words "d arcy". So every apostrophed or particled
   surname failed silently, and the estate's most important connector went
   with it: Falco's generation nine married Ian Kenneth D'Arcy, the join
   between two of these archives, and the row would not say so.
   Matched as a whole phrase on word boundaries instead. */
const matchIn = (needles, name) => {
  const hay = text(name);
  if (hay.trim().length < 2) return null;
  return [...needles]
    .filter(Boolean)
    .sort((a, b) => String(b).length - String(a).length)   // "Defranceschi" beats a stray "de"
    .find((n) => {
      const f = fold(n).trim();
      if (!f || f.length < 3 || STOP.has(f)) return false;
      return hay.includes(" " + f + " ");
    });
};

export function surnameDoors(name, { own = "", families = [], ring = [] } = {}) {
  const out = [];
  if (!name) return out;
  const maiden = maidenPart(name);
  const passes = maiden ? [maiden, name] : [name];

  const fams = Array.isArray(families) ? families : [];
  outer: for (const text of passes) {
    for (const f of fams) {
      const names = (f.surnames && f.surnames.length ? f.surnames : [f.label]).filter(Boolean);
      if (matchIn(names, text)) { out.push({ label: f.label, href: f.href, external: false }); break outer; }
    }
  }

  const sites = Array.isArray(ring) ? ring : Object.values(ring || {}).find(Array.isArray) || [];
  ringPass: for (const text of passes) {
    for (const a of sites) {
      if (!a || a.key === own) continue;
      if (matchIn(a.surnames || [], text)) {
        out.push({ label: a.name, href: a.url, external: true });
        break ringPass;
      }
    }
  }
  return out;
}

export default surnameDoors;
