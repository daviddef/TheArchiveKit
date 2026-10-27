/* Who is on our direct line, from the archive's ONE file src/data/direct-line.json (kit/docs/family-ribbon.md, "The direct line").
 *
 *   { "generationLabel": "generation",
 *     "people":   [{ slug, generation, storyChapter, name? }],             the story ribbon's persons, one per card
 *     "partners": [{ slug, generation, storyChapter, partnerOf, name? }],  the spouses on those cards who are themselves direct ancestors
 *     "unlinked": [{ generation, storyChapter, name? }] }                  the ribbon cards that name no person page (a living
 *                                                                          generation the archive has not given one): they are
 *                                                                          on the line all the same, and tinted as "gen:N"
 *
 * The file is PRODUCED from the story (kit/tools/directline.py --story src/data/story.json --write src/data/direct-line.json)
 * and held to it by the gate (kit/tools/checkfamilyribbon.py: people equals the story ribbon's persons, generation and chapter
 * included). Every component that tints (`is-ours`) asks this file and nothing else, so the tint cannot drift from the story.
 *
 * Plain functions, no Astro, no JSON imports: kit/tools/familyribbon_logic.mjs holds them to cases. */

export const OURS_LEGEND = "tinted = our direct line";

/* slug -> { slug, generation, storyChapter, role: "line" | "partner", partnerOf?, name? } */
export function directMap(dl) {
  const m = new Map();
  for (const p of (dl && dl.people) || []) if (p && p.slug) m.set(String(p.slug), { ...p, role: "line" });
  for (const p of (dl && dl.partners) || []) if (p && p.slug && !m.has(String(p.slug))) m.set(String(p.slug), { ...p, role: "partner" });
  return m;
}
/* The entry of a STORY RIBBON card: by its person, else (no person) by its number in the ribbon. The key is what the card
   prints as data-ours: the slug, or "gen:N". */
export function cardEntry(dl, card, index) {
  const m = directMap(dl);
  if (card && card.person) return m.get(String(card.person)) || null;
  const u = ((dl && dl.unlinked) || []).find((x) => x.generation === index + 1);
  return u ? { ...u, role: "unlinked" } : null;
}
export const cardKey = (card, index) => (card && card.person ? String(card.person) : `gen:${index + 1}`);
export const oursOf = (dl, slug) => (slug ? directMap(dl).get(String(slug)) || null : null);
export const isOurs = (dl, slug) => !!oursOf(dl, slug);

/* "On our direct line · generation 7" (the noun is the archive's: generationLabel) */
export function bandText(entry, dl) {
  if (!entry) return "";
  const noun = (dl && dl.generationLabel) || "generation";
  return `On our direct line · ${noun} ${entry.generation}`;
}
/* where the band's "in the story" link goes: the story page and the chapter's id */
export const storyLink = (entry, storyBase = "/story/") => (entry && entry.storyChapter ? `${storyBase.replace(/#.*$/, "")}#${entry.storyChapter}` : storyBase);

/* The file, made from a story: one entry per ribbon card with a person; a card that says `spouseDirect: true` and names a
   `spousePerson` adds that spouse as a partner (the spouse is also our ancestor: a mother is). Cards are generations in
   order, earliest first, numbered from 1 as the ribbon numbers them. */
export function fromStory(book, { generationLabel = "generation" } = {}) {
  const people = [], partners = [], unlinked = [];
  ((book && book.ribbon && book.ribbon.cards) || []).forEach((c, i) => {
    if (c.person) people.push({ slug: c.person, generation: i + 1, storyChapter: c.chapter, name: c.name });
    else unlinked.push({ generation: i + 1, storyChapter: c.chapter, name: c.name });
    if (c.spouseDirect && c.spousePerson) partners.push({ slug: c.spousePerson, generation: i + 1, storyChapter: c.chapter, partnerOf: c.person || "", name: c.spouse });
  });
  return { generationLabel, people, partners, unlinked };
}
