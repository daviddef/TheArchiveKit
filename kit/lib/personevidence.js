/* WHAT AN ARCHIVE HOLDS FOR A PERSON, as a mark (PERSON-PAGE-SPEC.md section 5; story mode, section 2a). Read only from what the archive's
   own row already says: the grades written into the person's note (`doc`, `inf`, `lore`, `tree`), a linked register image (`ark`), and the
   source kind the row was made from (`src`). It describes the PERSON, never the link to them: a link takes a grade only where the archive has
   tested one (`linkTable`), and a mark on a card says so only there. Nothing is inferred from a ribbon's position, which is about where a
   person stands in a story and not about a register.
   The words are the kit's (ruled 16 October 2026): a PERSON takes a grade (Documented, Inferred, Family), a LINK takes a source word (a record
   read here, inferred, family tree unverified), and being on the direct line is the bar above the page, never a mark. So a person placed on
   the line by argument alone, or kept under a line, carries no mark here.
   tiers: doc (Documented), inf (Inferred), lore and tree (Family). */
export const gradesIn = (note) => new Set([...String(note || "").matchAll(/[*`](doc|inf|lore|tree)[*`]/g)].map((m) => m[1]));

/* `docSrc` is the set of the archive's own source kinds that mean «a register or record was read» (an archive names its kinds; the kit does
   not), and `treeSrc` those that mean «a family tree, unverified». With neither, only the grades the author wrote and a linked register image
   (`ark`) count. */
export function evidenceOf(row, { docSrc = [], treeSrc = [] } = {}) {
  if (!row) return null;
  const g = gradesIn(row.note);
  if (row.ark || g.has("doc") || docSrc.includes(row.src)) return { tier: "doc", label: "Documented" };
  if (g.has("lore") && !g.has("inf")) return { tier: "lore", label: "Family" };
  if (g.has("inf")) return { tier: "inf", label: "Inferred" };
  if (treeSrc.includes(row.src)) return { tier: "tree", label: "Family" };
  return null;
}

/* the grade this archive has given a parent-child (or marriage) link, from family-links.json: «our|their» → {relation, grade} */
export function linkTable(familyLinks) {
  const out = {};
  const walk = (o) => {
    if (Array.isArray(o)) o.forEach(walk);
    else if (o && typeof o === "object") {
      if (o.ourSlug && o.theirSlug && o.grade) { out[`${o.ourSlug}|${o.theirSlug}`] = { relation: o.relation, grade: o.grade }; out[`${o.theirSlug}|${o.ourSlug}`] = out[`${o.theirSlug}|${o.ourSlug}`] || { relation: o.relation, grade: o.grade, reverse: true }; }
      Object.values(o).forEach(walk);
    }
  };
  walk(familyLinks);
  return out;
}
