/* The arithmetic and the words behind the lines drawing (components/BranchRivers.astro), in one place so the
   component, its logic test (kit/tools/lines_logic.mjs) and the gate (kit/tools/checklines.py, which re-implements
   the same rules in Python on purpose) can be held to one another.

   THE CONTRACT, in one paragraph. A drawing is `{lanes, pens, bridges, ...}`. Everything below the first line of this
   list is NEW (the 2nd-round extension) and OPTIONAL; data written for the old component draws exactly as it did.

     lane    { key, colour, label, href, read, nodes, ends,           // as always
               conf,                                                  // the legacy status line, a free string
               status,     'documented' | 'inferred' | 'origin-unknown' | 'family-lore'
               statusNote, the words after the tier ("Carnian", "at Ližnjan from 1815 · origin still not found")
               span,       [first, last] the first and last DOCUMENTED year; last may be null ("from 1628")
               members }   people slugs on this lane that are not a node
     node    [place, year, why]  or  { place, year, why, person, evidence }
               person      a person page (a slug, or a path): the node links to the person, not to the page top
               evidence    where the node rests: read | indexed | scanned | tree | inferred | disputed | none
                           (the person page's own words; anything else is refused by the gate)
     pen     { id, kind, head, note, items, members, count }
               kind        'not-yet-placed' | 'different-stock'
               items       [name, href, why] households or clusters, drawn as dots
               members     people slugs (or { person, reason }) in the pen
               count       how many PEOPLE the pen holds: equals members.length when members is given
               note        the explanation printed under the pen
     legacy  unplaced / loose / unplacedHead / looseHead / looseNote become two pens (kind 'not-yet-placed' and
             'different-stock'); unplacedNote is new. When `pens` is an array the legacy keys are ignored.

   WHAT A STATUS MEANS. It is how far back the lane's EVIDENCE reaches, not how interesting the lane is:
     documented      every step on the lane, its beginning included, rests on a document
     inferred        documented over `span`, and where it came from is inferred (the note says to what)
     origin-unknown  documented over `span`, and where it came from has not been found
     family-lore     nothing on the lane is documented; it is told, not read. A lane of this kind has no span.
   The words the reader sees are made here, from the fields, so two lanes in two archives that mean the same thing
   say the same thing. `conf`, the older free string, is drawn only when a lane has no `status`. */
import { SOURCES, readSource } from "./person.js";
import { plain } from "./md.js";

export const STATUSES = ["documented", "inferred", "origin-unknown", "family-lore"];
export const PEN_KINDS = ["not-yet-placed", "different-stock"];
export const NODE_EVIDENCE = ["read", "indexed", "scanned", "tree", "inferred", "disputed", "none"];

export const HEAD_DEFAULT = {
  "not-yet-placed": "Real households of the name — not yet placed on any of these lines",
  "different-stock": "Attached to no line here — a different stock of a very common name",
};
/* what the pen is for, said once: used for the aria-label and the phone list, never in place of the archive's note */
export const KIND_WORD = { "not-yet-placed": "not yet placed", "different-stock": "a different stock" };

const yr = (v) => {
  if (v == null || v === "") return null;
  const m = /^\s*(\d{3,4})\s*$/.exec(String(v));
  return m ? +m[1] : null;
};

/* "1628–1791" / "from 1628" / "to 1791" / "" */
export function spanText(span) {
  if (!Array.isArray(span)) return "";
  const a = yr(span[0]), b = yr(span[1]);
  if (a && b) return a === b ? String(a) : `${a}–${b}`;
  if (a) return `from ${a}`;
  if (b) return `to ${b}`;
  return "";
}

/* The status line of one lane: { tier, text, legacy }.
   - no `status`: the old `conf` string, untouched (`legacy: true`, `tier: null`)
   - documented: "Documented 1628–1791", then the note if there is one
   - inferred / origin-unknown: "Documented 1628–1791 · " then the note, else "origin inferred" / "origin not found";
     with no span the word "Documented" is not claimed: the line is just the note or the default
   - family-lore: "Family lore · " then the note, else "not documented" */
export function statusLine(lane) {
  const tier = lane && STATUSES.includes(lane.status) ? lane.status : null;
  if (!tier) return { tier: null, text: String((lane && lane.conf) ?? ""), legacy: true };
  const sp = spanText(lane.span);
  const note = plain(lane.statusNote ?? "");
  const lead = tier === "family-lore" ? "Family lore" : sp ? `Documented ${sp}` : "";
  const dflt = { documented: "", inferred: "origin inferred", "origin-unknown": "origin not found", "family-lore": "not documented" }[tier];
  const tail = note || dflt;
  const text = lead && tail ? `${lead} · ${tail}` : lead || tail || "Documented";
  return { tier, text, legacy: false };
}

export const TIER_WORD = {
  documented: "documented", inferred: "origin inferred", "origin-unknown": "origin unknown", "family-lore": "family lore",
};

/* ---------------------------------------------------------------- nodes, ends, pens */

/* A node or an end may be the old array or an object; both come out as one shape. Anything past the third array
   slot is kept as `extra` (an archive passed a snapshot id there) and never read. */
export function node(n, kind = "node") {
  if (Array.isArray(n)) {
    return kind === "end"
      ? { place: String(n[0] ?? ""), href: n[1] ?? "", why: n[2] ?? "", extra: n.slice(3) }
      : { place: String(n[0] ?? ""), year: n[1] ?? "", why: n[2] ?? "", extra: n.slice(3) };
  }
  const o = n || {};
  return { place: String(o.place ?? o.name ?? ""), year: o.year ?? "", href: o.href ?? "", why: o.why ?? "",
           person: o.person ?? null, evidence: o.evidence ?? null, count: o.count ?? null, extra: [] };
}

/* the evidence word for a node: { key, label } or null when none was given. An unknown word is KEPT, visibly,
   as `unmarked` (person.js's own rule), never guessed at. */
export function evidenceOf(ev) {
  if (ev == null || ev === "") return null;
  const r = readSource(ev);
  return { key: r.source, label: SOURCES[r.source].label, known: r.known, soft: r.source !== "read" };
}

/* the path a `person` value points at. A slug is looked up under `personBase`; anything with a slash is a path. */
export function personPath(person, personBase = "/people/") {
  if (!person) return "";
  const s = String(person).trim();
  if (!s) return "";
  if (s.startsWith("/")) return s;
  if (s.includes("/")) return "/" + s;
  const b = personBase.endsWith("/") ? personBase : personBase + "/";
  return `${b}${s}/`;
}

/* a readable name for a slug when the page was given none: "lucia-defranceschi-1844" → "Lucia Defranceschi 1844" */
export function slugName(slug) {
  const s = String(slug ?? "").replace(/\/+$/, "").split("/").pop() ?? "";
  return s.split(/[-_]+/).filter(Boolean).map((w) => (/^\d/.test(w) ? w : w[0].toUpperCase() + w.slice(1))).join(" ");
}

/* members: a slug or { person, reason, name } → { person, reason, name } */
export function member(m) {
  if (m && typeof m === "object") return { person: String(m.person ?? m.slug ?? ""), reason: m.reason ?? "", name: m.name ?? "" };
  return { person: String(m ?? ""), reason: "", name: "" };
}

/* The pens, in the order they are drawn. `pens` wins when it is an array; otherwise the two legacy lists become two
   pens. A pen "holds something" when it has an item or a member: an empty heading is a claim the archive has looked
   and found nothing, and nobody has said so, so such a pen is not drawn. */
export function pensOf(rivers) {
  const r = rivers || {};
  let raw;
  if (Array.isArray(r.pens)) raw = r.pens;
  else {
    raw = [];
    if ((r.unplaced || []).length) raw.push({ id: "unplaced", kind: "not-yet-placed", head: r.unplacedHead, note: r.unplacedNote, items: r.unplaced });
    if ((r.loose || []).length) raw.push({ id: "loose", kind: "different-stock", head: r.looseHead, note: r.looseNote, items: r.loose });
  }
  return raw.map((p, i) => {
    const kind = PEN_KINDS.includes(p.kind) ? p.kind : "not-yet-placed";
    const items = (p.items || []).map((it) => {
      const o = node(it, "end");
      return { name: o.place, href: o.href, why: o.why, person: o.person ?? null, count: o.count ?? null };
    });
    const members = (p.members || []).map(member).filter((m) => m.person);
    const people = members.length ? members.length : (Number.isInteger(p.count) ? p.count : null);
    return {
      id: String(p.id ?? `pen-${i + 1}`), kind, head: p.head || HEAD_DEFAULT[kind], note: p.note ? String(p.note) : "",
      items, members, people, own: !!p.head,
    };
  }).filter((p) => p.items.length > 0 || p.members.length > 0);
}

/* "8 households · 31 people" (a different-stock pen says "3 kept apart", since what it holds is not households) — the count in a pen's heading, derived so it cannot go stale */
export function penCount(p) {
  const out = [];
  if (p.items.length) out.push(p.kind === "different-stock" ? `${p.items.length} kept apart` : `${p.items.length} ${p.items.length === 1 ? "household" : "households"}`);
  if (p.people != null) out.push(`${p.people} ${p.people === 1 ? "person" : "people"}`);
  return out.join(" · ");
}

/* Greedy line-break of a plain sentence for SVG text, which does not wrap. `max` is characters per line. A word longer
   than the line goes on a line of its own. */
export function wrap(text, max = 150) {
  const words = plain(text).split(" ").filter(Boolean);
  const out = [];
  let cur = "";
  for (const w of words) {
    if (cur && (cur + " " + w).length > max) { out.push(cur); cur = w; }
    else cur = cur ? cur + " " + w : w;
  }
  if (cur) out.push(cur);
  return out;
}

/* a label that must fit a column: cut at a word, with an ellipsis; the full text stays in the <title> */
export function clip(s, max = 34) {
  const t = String(s ?? "");
  if (t.length <= max) return t;
  const cut = t.slice(0, max - 1);
  const sp = cut.lastIndexOf(" ");
  return (sp > max * 0.5 ? cut.slice(0, sp) : cut).replace(/[\s,;:—-]+$/, "") + "…";
}

/* The people on a lane: the nodes' persons and the lane's own members, each once. */
export function lanePeople(lane) {
  const seen = new Set();
  for (const n of lane.nodes || []) { const o = node(n); if (o.person) seen.add(String(o.person)); }
  for (const m of lane.members || []) { const s = member(m).person; if (s) seen.add(s); }
  return [...seen];
}

/* Everything that can be counted, from the data, once. This is what a page should print instead of typing a number:
   «Seven families, eight unplaced households» goes stale the day a lane is added; ledger(rivers).lanes does not. */
export function ledger(rivers) {
  const lanes = (rivers && rivers.lanes) || [];
  const pens = pensOf(rivers);
  const byKind = (k) => pens.filter((p) => p.kind === k);
  const sum = (a, f) => a.reduce((n, x) => n + f(x), 0);
  const tiers = Object.fromEntries(STATUSES.map((s) => [s, lanes.filter((l) => l.status === s).length]));
  return {
    lanes: lanes.length,
    tiers,
    unstated: lanes.filter((l) => !STATUSES.includes(l.status)).length,
    bridges: ((rivers && rivers.bridges) || []).length,
    households: sum(byKind("not-yet-placed"), (p) => p.items.length),
    otherStock: sum(byKind("different-stock"), (p) => p.items.length),
    pens: pens.length,
    peopleOnLanes: new Set(lanes.flatMap(lanePeople)).size,
    peopleInPens: sum(pens, (p) => p.people ?? 0),
  };
}
