/* The pure half of components/FlagMini.astro: which of a ribbon card's mini flags may be drawn, the words that go with them, and the
   small script that keeps them from ever making a card taller. The flags are WORKED OUT by kit/tools/ribbonflags.py (the era
   snapshot, kit/data/regime-flags.json, the Flags Atlas's flag years) and written to the card as `flags`; checkribbonflags.py
   recomputes every one. A line has at most two: the ERA flag (the state that held the place in the card's year) and, only where it is
   another country's flag, TODAY's (the country the place is in now); or today's alone where the era cannot be said. They are drawn
   as one strip in the card's header row (stripOf). This file draws what the data says and refuses
   what must never be drawn whatever the data says (the same stance as the story's living rule):
     - a flag with no label, no file, of no known kind, or on a line that is not from / at / spouse;
     - two era flags or two today flags on one line, or a today flag of the same country as the era flag beside it;
     - on a living card (or a minor, or a living spouse's line) an era flag, or any flag with a year.
   The contract is kit/docs/ribbon-flags.md. No import: node runs it as a build does (kit/tools/ribbonflags_logic.mjs). */

export const FLAG_CREDIT = "Flags: Flags Atlas, by David Defranceski, drawn for this project";
export const FLAG_KEY = "Flags at a card's top: each place's state then, and today's where it differs (hover for which place).";
export const FLAG_LINES = ["from", "at", "spouse"];
export const FLAG_GRADES = ["doc", "inf", "lore"];
export const FLAG_KINDS = ["era", "today"];
export const FLAG_FILE = /^[a-z0-9]+(?:-[a-z0-9]+)*--era-[a-z0-9]+(?:-[a-z0-9]+)*\.svg$/;
const YEARISH = /(?<!\d)\d{4}(?!\d)/;
const country = (f) => String(f.svg).split("--")[0];

/* A living (or minor) card, or a living spouse's line: today's country flag only, never a year. */
export function livingLine(card, line) {
  if (card && (card.living || card.minor)) return true;
  return line === "spouse" && !!(card && (card.spouseLiving || card.spouseMinor));
}

/* The flags (era first, then today; at most one of each) the card may draw on a line; empty: draw nothing. */
export function flagsOn(card, line) {
  if (!card || !Array.isArray(card.flags) || !FLAG_LINES.includes(line)) return [];
  const mine = card.flags.filter((f) => f && f.line === line);
  const good = (f) => FLAG_KINDS.includes(f.kind) && typeof f.label === "string" && f.label.trim() !== "" && typeof f.svg === "string" && FLAG_FILE.test(f.svg);
  if (!mine.every(good)) return [];
  const era = mine.filter((f) => f.kind === "era"), today = mine.filter((f) => f.kind === "today");
  if (era.length > 1 || today.length > 1) return [];
  if (livingLine(card, line) && (era.length || today.some((f) => (f.year !== null && f.year !== undefined) || YEARISH.test(f.label)))) return [];
  if (today.length && today.some((f) => f.year !== null && f.year !== undefined)) return [];
  if (era.length && today.length && country(era[0]) === country(today[0])) return [era[0]];
  return [...era, ...today];
}

/* Does any card of a ribbon draw a flag? (then the ribbon prints the key and the credit, and the fitting script) */
export const hasFlags = (cards) => (cards || []).some((c) => FLAG_LINES.some((l) => flagsOn(c, l).length > 0));

/* A flag's ring follows the card's evidence: solid documented, dashed inferred, dotted family memory (today's too). */
export const flagClass = (f) => `flag-mini flag-mini-${FLAG_GRADES.includes(f && f.grade) ? f.grade : "doc"}${f && f.kind === "today" ? " flag-mini-today" : ""}`;

/* The image's address from the build's map of the kit's flag files ({"../data/flags/<file>": url}), or null. */
export function flagSrc(art, f) {
  if (!art || !f || typeof f.svg !== "string" || !FLAG_FILE.test(f.svg)) return null;
  const k = Object.keys(art).find((p) => p.endsWith("/" + f.svg));
  return k ? art[k] : null;
}

/* THE STRIP. A card's flags drawn once each, in the card's header row (components/FlagMini.astro): the from line's, then the at
   line's, then the spouse's, each line era first; a flag that two lines share is one slot whose words name both places ("from
   Canelones: Uruguay today; at Montevideo: Uruguay today"). At most FLAG_CAP marks: past it, FLAG_CAP - 1 flags and a "+n" whose
   words list the rest. A slot that holds a from line's flag carries the card's evidence ring (dashed inferred, dotted lore).
   -> { slots: [{flag, svg, kind, lines, label, grade, fromLine}], more: [labels] } */
export const FLAG_CAP = 4;
export function stripOf(card) {
  const slots = [];
  for (const line of FLAG_LINES) {
    for (const f of flagsOn(card, line)) {
      const s = slots.find((x) => x.svg === f.svg);
      if (s) { s.lines.push(line); s.labels.push(f.label); s.fromLine ||= line === "from"; s.kind = s.kind === f.kind ? s.kind : "both"; }
      else slots.push({ flag: f.flag, svg: f.svg, kind: f.kind, lines: [line], labels: [f.label], grade: f.grade, fromLine: line === "from" });
    }
  }
  slots.forEach((s) => { s.label = s.labels.join("; "); });
  if (slots.length <= FLAG_CAP) return { slots, more: [] };
  return { slots: slots.slice(0, FLAG_CAP - 1), more: slots.slice(FLAG_CAP - 1).map((s) => s.label) };
}

/* A slot's class: the evidence ring only where it holds the from line's flag; "today" where it is today's flag only. */
export const slotClass = (s) => `flag-mini flag-mini-${s.fromLine && FLAG_GRADES.includes(s.grade) ? s.grade : "doc"}${s.kind === "today" ? " flag-mini-today" : ""}`;
