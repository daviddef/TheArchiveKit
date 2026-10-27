/* The logic under the family ribbon (components/FamilyRibbon.astro): everything it decides that is not drawing, so that the
 * component stays thin, the archives agree, and kit/tools/familyribbon_logic.mjs and kit/tools/checkfamilyribbon.py (which
 * re-implements the same rules in Python on purpose) can be held to one another. The contract is kit/docs/family-ribbon.md.
 *
 * A FAMILY RIBBON is one family's own line of generations, drawn as the story's ribbon is, smaller. Under it, HOW OUR LINE
 * CONNECTS: one block for each place the archive's direct line (the story ribbon) touches this family, or, if it does not,
 * a quiet block that says so.
 *
 *   card         the story's card, exactly (kit/lib/story.js RIBBON_FIELDS) plus person, spousePerson, spouseHref, title, glyph
 *   connection   { ourSlug, ourGeneration, theirSlug, theirName, relation, grade, storyHref, note?, theirOrigin?, ourName? }
 *                relation is OUR person's toward THEIR person: Ljubomir (ours) "married" Milka Papić (theirs); Hedviga
 *                (ours) "daughter of" Milka Papić. So a block reads left to right: our person, the relation, their person.
 *   notConnected { why }  what is missing, in the archive's words
 */
import { GRADES, GRADE_WORD, RIBBON_FIELDS, yearsLine, atLine } from "./story.js";
import { statusLine, STATUSES } from "./lines.js";
import { directMap } from "./directline.js";

export { GRADES, GRADE_WORD, STATUSES };
export const CARD_FIELDS = RIBBON_FIELDS;            // name, years, origin, originGrade, spouse, spouseOrigin, atPlace, atYear, living

/* The words a relation is printed as. `needsDoc`: said only of a relation a document states (a godparent is in a baptism
   entry or it is nothing). Both directions are listed because the archive writes the relation as it reads from our person. */
export const RELATIONS = {
  "married":        { word: "married",        needsDoc: false },
  "son of":         { word: "son of",         needsDoc: false },
  "daughter of":    { word: "daughter of",    needsDoc: false },
  "child of":       { word: "child of",       needsDoc: false },
  "father of":      { word: "father of",      needsDoc: false },
  "mother of":      { word: "mother of",      needsDoc: false },
  "parent of":      { word: "parent of",      needsDoc: false },
  "brother of":     { word: "brother of",     needsDoc: false },
  "sister of":      { word: "sister of",      needsDoc: false },
  "sibling of":     { word: "sibling of",     needsDoc: false },
  "godparent of":   { word: "godparent of",   needsDoc: true },
  "godchild of":    { word: "godchild of",    needsDoc: true },
  "witness for":    { word: "witness for",    needsDoc: true },
};
export const RELATION_NAMES = Object.keys(RELATIONS);
export const relationWord = (r) => (RELATIONS[r] ? RELATIONS[r].word : String(r || ""));

/* family-level status: the same four tiers, the same words, as the lines page */
export const familyStatus = (fam) => statusLine({ status: fam && fam.status, statusNote: fam && fam.statusNote, span: fam && fam.span });

/* ---- the cards -------------------------------------------------------------------------------------------------- */

/* The slugs a card is about: the person and the spouse. A connection's `theirSlug` is one of these, or a person page. */
export const cardSlugs = (c) => [c.person, c.spousePerson].filter(Boolean).map(String);

/* A card is on our direct line when its person is in direct-line.json. Its SPOUSE is tinted only through the spouse line
   (the partner), never the card: a card is one generation's person. */
export function cardOurs(card, dl) {
  const m = directMap(dl);
  return card.person && m.has(String(card.person)) ? m.get(String(card.person)) : null;
}
/* a spouse who is herself on our direct line, for a small mark in the spouse line */
export function spouseOurs(card, dl) {
  const m = directMap(dl);
  return card.spousePerson && m.has(String(card.spousePerson)) ? m.get(String(card.spousePerson)) : null;
}

/* What a family card prints, the living rule applied here as well as in the gate: a living card prints no years and no
   year on its "at" line; a minor (living, with an initial for a name) prints its initial and nothing else. */
export const cardYears = yearsLine;
export const cardAt = atLine;

/* ---- cards from a lane of lines.json ---------------------------------------------------------------------------- */

/* evidence word of a lane node -> the ribbon's grade. A node with no evidence takes its lane's tier. Nothing is promoted: an
   index, a scan and an inference are all "inf" at best, a tree is "lore", and a lane of family lore is lore throughout. */
const EVIDENCE_GRADE = { read: "doc", indexed: "inf", scanned: "inf", inferred: "inf", tree: "lore", disputed: "lore", none: "lore" };
const LANE_GRADE = { documented: "doc", inferred: "inf", "origin-unknown": "inf", "family-lore": "lore" };
export function nodeGrade(node, lane) {
  const ev = node && node.evidence;
  if (ev && EVIDENCE_GRADE[ev]) return EVIDENCE_GRADE[ev];
  return LANE_GRADE[lane && lane.status] || "lore";
}

/* The lane for { set, key }: lines.json is {sets:[{slug|name, lanes}]}, a drawing, or a list of drawings. */
export function findLane(lines, ref) {
  if (!lines || !ref) return null;
  const sets = Array.isArray(lines) ? lines : lines.sets || [lines];
  for (const s of sets) {
    if (ref.set && ![s.slug, s.name, s.key].includes(ref.set)) continue;
    const lane = (s.lanes || []).find((l) => l.key === ref.key);
    if (lane) return lane;
  }
  return null;
}

/* A lane's nodes are PLACES along a line, some of which are a person (a node with `person`). The ribbon's cards are the
   persons, in the order of the lane. A node with no person (a marriage, an inn, a death) is an event, not a generation, and
   is not a card; `skipped` says how many, so the page can say it. `people` is the archive's own {slug: {name, years, living,
   minor, origin, originGrade, spouse, spouseOrigin, spousePerson, atPlace, atYear}}: what the lane does not hold. Nothing is
   guessed: a node whose person is not in `people` is skipped, and listed in `unresolved`. */
export function cardsFromLane(lane, people = {}) {
  const cards = [], unresolved = [];
  let skipped = 0;
  for (const raw of (lane && lane.nodes) || []) {
    const n = Array.isArray(raw) ? { place: raw[0], year: raw[1], why: raw[2] } : raw || {};
    if (!n.person) { skipped += 1; continue; }
    const slug = String(n.person).replace(/^\/people\//, "").replace(/\/+$/, "");
    const p = people[slug];
    if (!p) { unresolved.push(slug); continue; }
    const living = !!p.living;
    cards.push({
      name: p.name, years: living ? "" : p.years || (n.year ? String(n.year) : ""),
      origin: p.origin || "", originGrade: p.originGrade || nodeGrade(n, lane),
      spouse: p.spouse || "", spouseOrigin: p.spouseOrigin || "",
      atPlace: p.atPlace || "", atYear: living ? "" : p.atYear || "", living,
      ...(p.minor ? { minor: true } : {}), person: slug,
      ...(p.spousePerson ? { spousePerson: p.spousePerson } : {}),
      ...(n.why ? { title: String(n.why).replace(/\s+/g, " ").slice(0, 220) } : {}),
    });
  }
  return { cards, skipped, unresolved };
}

/* ---- the connection blocks --------------------------------------------------------------------------------------- */

/* One block, ready to draw. The names come from the connection, else from direct-line.json (ours) and the family's cards
   (theirs); the generation from direct-line.json, so a block cannot name a generation the story does not have. */
export function blocksOf(family, dl, { cards = family.cards || [] } = {}) {
  const dm = directMap(dl);
  const byTheir = new Map();
  for (const c of cards) {
    if (c.person) byTheir.set(String(c.person), c);
    if (c.spousePerson) byTheir.set(String(c.spousePerson), { ...c, name: c.spouse, origin: (c.spouseOrigin || "").replace(/^of\s+/, ""), _spouse: true });
  }
  const conns = (family.connections || []).map((c) => {
    const ours = dm.get(String(c.ourSlug));
    const theirCard = byTheir.get(String(c.theirSlug));
    return {
      kind: "link",
      ourSlug: c.ourSlug, ourName: c.ourName || (ours && ours.name) || c.ourSlug,
      ourGeneration: ours ? ours.generation : c.ourGeneration,
      theirSlug: c.theirSlug, theirName: c.theirName || (theirCard && theirCard.name) || c.theirSlug,
      theirOrigin: c.theirOrigin || (theirCard ? (theirCard._spouse ? theirCard.spouseOrigin : theirCard.origin && `from ${theirCard.origin}`) : "") || "",
      relation: c.relation, word: relationWord(c.relation), grade: c.grade, storyHref: c.storyHref || "", note: c.note || "",
    };
  });
  if (conns.length) return conns.sort((a, b) => (a.ourGeneration || 0) - (b.ourGeneration || 0));
  const why = family.notConnected && family.notConnected.why ? String(family.notConnected.why) : "";
  return [{ kind: "none", why }];
}

/* "Gen. 7 Ljubomir Blažević married Milka Papić, of Senj (documented)": the block as a sentence, for its aria-label */
export function blockSentence(b) {
  if (b.kind === "none") return `Not connected to our line yet${b.why ? ": " + b.why : ""}`;
  return `Our line, generation ${b.ourGeneration}: ${b.ourName} ${b.word} ${b.theirName}${b.theirOrigin ? ", " + b.theirOrigin.replace(/^from /, "of ") : ""} (${GRADE_WORD[b.grade] || "ungraded"})`;
}

/* which of a family's cards touch our line: theirSlug -> [our generations], so the card can carry a small mark */
export function joinsOf(family) {
  const out = new Map();
  for (const c of family.connections || []) {
    const g = c.ourGeneration;
    out.set(String(c.theirSlug), [...(out.get(String(c.theirSlug)) || []), g]);
  }
  return out;
}

/* Marriages read from the story's own ribbon: every card with a person and a spousePerson is a "married" connection
   between our person and a person of ANOTHER family. `familyOf(slug)` is the archive's (which family page the spouse
   belongs to); a spouse it cannot place is left out, not guessed. The grade is the card's originGrade, the weakest the
   card admits: an archive that knows the marriage is better documented than the origin says so by supplying the
   connection itself, and its own connection wins. Returns {familyId: [connection]}. */
export function marriageConnections(ribbon, familyOf, { storyBase = "/story/" } = {}) {
  const out = {};
  ((ribbon && ribbon.cards) || []).forEach((c, i) => {
    if (!c.person || !c.spousePerson) return;
    const fam = familyOf(c.spousePerson);
    if (!fam) return;
    (out[fam] ||= []).push({
      ourSlug: c.person, ourGeneration: i + 1, ourName: c.name, theirSlug: c.spousePerson, theirName: c.spouse,
      theirOrigin: c.spouseOrigin || "", relation: "married", grade: c.originGrade || "lore", storyHref: `${storyBase}#${c.chapter}`,
    });
  });
  return out;
}

/* A family's connections: those it states, then the story's marriages for it that it does not already state (same our
   person and same their person), in the order of the generations. */
export function mergeConnections(stated = [], derived = []) {
  const key = (c) => `${c.ourSlug}|${c.theirSlug}`;
  const have = new Set(stated.map(key));
  return [...stated, ...derived.filter((c) => !have.has(key(c)))].sort((a, b) => (a.ourGeneration || 0) - (b.ourGeneration || 0));
}
