/* The logic under the family story page (kit/docs/story.md): everything the components decide that is not drawing.
 * Plain functions, no Astro, no JSON imports, so kit/tools/story_logic.mjs can hold them to cases under Node and the
 * components can stay thin.
 *
 * THE GRAMMAR (the same words in the data, the page and the gate):
 *   grades    doc  a document says so          (solid line, solid outline)
 *             inf  the archive reasons it      (dashed)
 *             lore family memory, a family chart or tree (dotted)
 *   registers people  what the papers say of these people; carries a grade
 *             world   "In the world around them": the place and the years, never these people; carries a source,
 *                     `archive` (this archive's own pages) or `history` (general history, listed in the notes)
 *   living    a living person is a filled node that says "living" or a first name, with NO dates at all; a minor is
 *             an initial and nothing else. The data carries `living: true` / `minor: true`; the gate holds the
 *             rest (kit/tools/checkfamilystory.py), and the layout here refuses to print a date for them anyway.
 */

export const GRADES = ["doc", "inf", "lore"];
export const SOURCES = ["archive", "history"];
export const GRADE_WORD = { doc: "documented", inf: "inferred", lore: "family memory or the family's tree", living: "living: named in the text only, no dates" };
export const MARK_TITLE = { doc: "Documented", inf: "Inferred", lore: "Family lore", archive: "From this archive's own pages", history: "General history" };
export const LEGEND = [["doc", "a document says so"], ["inf", "the archive reasons it from documents"], ["lore", "family memory, the family chart or the family's tree"]];

/* A minor shows as initials: one to three capital letters, each optionally followed by a stop. */
export const isInitial = (name) => /^(?:\p{Lu}\.?){1,3}$/u.test(String(name ?? "").trim());

/* A year or a date: four digits that can only be a year (1000-2099), or a day and a month name. */
const MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec";
export const YEAR_RE = /(?<![\d.,-])(?:1[0-9]{3}|20[0-9]{2})(?![\d])/;
export const DATE_RE = new RegExp(`\\b\\d{1,2}(?:st|nd|rd|th)?\\s+(?:${MONTHS})\\b|\\b(?:${MONTHS})\\s+\\d{1,2}\\b`);
export const hasDate = (s) => YEAR_RE.test(String(s ?? "")) || DATE_RE.test(String(s ?? ""));

/* ---- prose ------------------------------------------------------------------------------------------------------
   The data is light markup: *italic*, **bold**, «quoted», and links written [words](target). A target is an internal
   path (/gologorica-line/#casa31), a full address, an #anchor on this page, or person:slug (a person's page, wherever the
   archive keeps them). The archive may pass its own renderer (`md`) if it already handles links; the default is the kit's
   md() with links done here, so that the kit's story reads the same in all eight. */
const LINK_RE = /\[([^\]\n]+)\]\(([^)\s]+)\)/g;
export function linkTarget(t, { u = (p) => p, personHref = (s) => `/people/${s}/` } = {}) {
  if (t.startsWith("person:")) return personHref(t.slice(7));
  if (t.startsWith("#") || /^https?:\/\//.test(t)) return t;
  return u(t);
}
export function proseHtml(text, md, opts = {}) {
  const links = [];
  /* a rec: link is the archive's own record link (the linking standard); its renderer handles it, so it is left in the text */
  const held = String(text ?? "").replace(LINK_RE, (m, words, target) => { if (target.startsWith("rec:")) return m; links.push(target); return `\u0002${links.length - 1}\u0003${words}\u0004`; });
  return md(held).replace(/\u0002(\d+)\u0003([\s\S]*?)\u0004/g, (_, i, words) => {
    const h = linkTarget(links[+i], opts);
    const ext = /^https?:\/\//.test(h) ? ' rel="noopener"' : "";
    return `<a href="${h.replace(/"/g, "&quot;")}"${ext}>${words}</a>`;
  });
}
/* The text with the markup taken off, for titles, alt text and the gate's name search. */
export const plainText = (s) => String(s ?? "").replace(LINK_RE, "$1").replace(/\*{1,3}(.+?)\*{1,3}/gs, "$1").replace(/«(.+?)»/gs, "$1").replace(/`/g, "").replace(/\s+/g, " ").trim();

/* ---- the book ---------------------------------------------------------------------------------------------------- */
export const chaptersOf = (book) => book.chapters || [];

/* "5 and 6": which generations of the ribbon a chapter tells. A chapter may state its own `generation` (a number or a list);
   otherwise the ribbon cards that point at it say. */
export function generationsOf(book) {
  const out = {};
  (book.ribbon?.cards || []).forEach((c, i) => { (out[c.chapter] ||= []).push(i + 1); });
  for (const c of chaptersOf(book)) if (c.generation != null) out[c.id] = [].concat(c.generation);
  const words = {};
  for (const [id, g] of Object.entries(out)) words[id] = g.length > 1 ? `${g.slice(0, -1).join(", ")} and ${g[g.length - 1]}` : String(g[0]);
  return words;
}

/* Which world paragraphs open a run (they carry the "In the world around them" label once per run). */
export const worldLeads = (paras) => paras.map((p, i) => p.register === "world" && (i === 0 || paras[i - 1].register !== "world"));

/* A paragraph's marks: one for a people paragraph (its grade), one per source for a world paragraph. */
export function marksOf(p) {
  const ev = p.evidence || [];
  if (p.register === "world") {
    return (ev.length ? ev : [{}]).map((e) => ({ kind: e.kind || p.worldSource, href: e.href, why: e.why }));
  }
  const e = ev[0] || {};
  return [{ kind: p.grade, href: e.href, why: e.why }];
}

export const paragraphsOf = (c) => (c.paragraphs || []).map((p, i) => ({ register: "people", ...p, id: p.id || `${c.id}-${i + 1}` }));
export const quotesOf = (c) => (c.quote ? [].concat(c.quote) : []);
export const conflictsFor = (book, id) => (book.conflicts || []).filter((x) => x.chapter === id);

/* ---- the ribbon -------------------------------------------------------------------------------------------------- */
export const RIBBON_FIELDS = ["name", "years", "origin", "originGrade", "spouse", "spouseOrigin", "atPlace", "atYear", "living"];

/* The line under the origin: "at Gracisce, 1819", from atPlace and atYear; nothing when there is no place. A living card prints
   no year whatever the data says. */
export function atLine(card) {
  if (!card.atPlace) return "";
  const yr = card.living ? "" : card.atYear;
  return `at ${card.atPlace}${yr ? ", " + yr : ""}`;
}
export const yearsLine = (card) => (card.living ? "" : card.years || "");

/* ---- the tree ---------------------------------------------------------------------------------------------------- */
export const GLYPHS = {
  hill: "M0 16L7 4L11 10L14 7L21 16Z",
  loom: "M1 2H20V16H1ZM5 2V16M9 2V16M13 2V16M17 2V16M1 9H20",
  field: "M0 6Q5 3 10 6T21 6M0 11Q5 8 10 11T21 11M0 16Q5 13 10 16T21 16",
  stone: "M1 7H20V16H1ZM6 7V11M14 11V16M3 2L9 6",
  wave: "M0 9Q3 5 6 9T12 9T18 9T24 9M0 15Q3 11 6 15T12 15T18 15T24 15",
  works: "M0 16V8L5 4V8L10 4V8L15 4V8L20 4V16ZM17 4V0H19V3",
  gable: "M1 16V8L10 1L19 8V16ZM8 16V11H12V16",
  ship: "M0 12H22L18 17H4ZM11 12V1L18 9H11",
};

/* Every node of a tree, in reading order. */
export function treeNodes(tree) {
  return (tree?.rows || []).flatMap((r) => (r.kind === "gap" ? [] : r.nodes || []));
}

/* What a node's name and years print as. A living node prints its name (or "living") and nothing else. */
export const nodeYears = (n) => (n.living ? "" : n.years || "");
export const nodeLabel = (n) => n.name;
export function nodeTip(n) {
  if (n.living) return n.name === "living" ? "A living person, drawn without name or dates" : `${n.name}: a living person, with no dates`;
  return `${n.name}${n.years ? ", " + n.years : ""} (${GRADE_WORD[n.grade] || "ungraded"})`;
}
/* Who the nodes of each `grandchildren` row belong to. A node says which child it is the child of with `of` (the id of a
   node in the nearest children row above it). With `of` omitted and exactly ONE child, the child is that one (the old
   contract, kept). Anything else is unresolved: the gate fails it (T4, T5), and the drawing puts it under the child who
   carries the thread, or the last child, so that nothing is lost, never silently under a guess the data did not make.
   Returns one entry per grandchildren row: {index, kids, groups: [{parent, nodes}] in the order of the children,
   loose: [nodes with no parent]}. */
export function grandchildGroups(tree) {
  const out = [];
  let kids = null;
  (tree?.rows || []).forEach((r, index) => {
    if (r.kind === "children") kids = r.nodes || [];
    else if (r.kind === "grandchildren") {
      const by = new Map(), loose = [];
      for (const g of r.nodes || []) {
        let p = null;
        if (kids) p = g.of ? kids.find((k) => k.id === g.of) || null : kids.length === 1 ? kids[0] : null;
        if (p) by.set(p, [...(by.get(p) || []), g]); else loose.push(g);
      }
      const groups = (kids || []).filter((k) => by.has(k)).map((k) => ({ parent: k, nodes: by.get(k) }));
      out.push({ index, kids, groups, loose });
    }
  });
  return out;
}

/* The faults the gate reports (checkfamilystory.py T4, T5) for the grandchildren rows of a tree, as codes, in reading order:
   the same answers on the shared cases in kit/data/story-cases.json. T4 a grandchild under a children row of more than one
   node that does not say whose it is; T5 an `of` that names no node in the children row above. */
export function grandchildFaults(tree) {
  const out = [];
  let kids = null;
  for (const r of tree?.rows || []) {
    if (r.kind === "children") kids = r.nodes || [];
    else if (r.kind === "grandchildren") {
      const ids = new Set((kids || []).map((k) => k.id).filter(Boolean));
      for (const n of r.nodes || []) {
        if ("of" in n) { if (!ids.has(n.of)) out.push("T5"); }
        else if (kids && kids.length > 1) out.push("T4");
      }
    }
  }
  return out;
}

/* "Cristina's children": the possessive of a name, and a nameless living parent as "the living person's". */
export const possessive = (n) => { const nm = n.living && n.name === "living" ? "the living person" : String(n.name); return /s$/i.test(nm) ? nm + "'" : nm + "'s"; };

export function treeAlt(tree, title) {
  const say = (p) => {
    if (p.living) return p.name === "living" ? "a living person" : `${p.name}, living`;
    return `${p.name}${p.years ? " " + p.years : ""}, ${GRADE_WORD[p.grade]}${p.id && p.id === tree.thread ? ", who carries the line" : ""}`;
  };
  /* inside a group the words "X's children" already say they are living-or-not family, so a living node is its name only */
  const sayKid = (p) => (p.living ? (p.name === "living" ? "a living person" : p.name) : say(p));
  const joined = (ns, f) => { const t = ns.map(f).join(ns.some((p) => !p.living) ? "; " : ", "); return t.endsWith(".") ? t.slice(0, -1) : t; };   // "A., M" + the sentence's stop
  const byRow = new Map(grandchildGroups(tree).map((g) => [g.index, g]));
  const rows = (tree.rows || []).map((r, i) => {
    if (r.kind === "gap") return `${r.text}.`;
    if (r.kind === "grandchildren" && byRow.has(i)) {
      const G = byRow.get(i);
      return [...G.groups.map((g) => `${possessive(g.parent)} children: ${joined(g.nodes, sayKid)}.`),
        ...(G.loose.length ? [`Grandchildren, of a parent the data does not name: ${joined(G.loose, sayKid)}.`] : [])].join(" ");
    }
    return (r.nodes || []).map(say).join("; ") + ".";
  });
  return `Family tree for ${title}. ${rows.join(" ")}`;
}

/* The geometry of a tree on a stem. Rows are drawn top to bottom:
     above         one person above the couple (a parent, or the earliest name the papers give)
     couple        two people in a box
     children      a column of ticks off the stem
     grandchildren each node hangs under ITS OWN parent (`of`), straight below that child: a short stem from the child's
                   own node, the grandchildren ticked off it. A child with none has no stem. (With no `of` and one child
                   they all hang under that child; see grandchildGroups.) A grandchildren row with no children row
                   above it is drawn as a column of its own.
     gap           a break the papers have not closed
   The thread (tree.thread, a node id) is the coloured line down the stem to the child who carries the line on into the
   next chapter. Returns the picture's size and the positions; the component only draws. */
export function layoutTree(tree, hasNext = false) {
  const W = 360, X0 = 22, KX = 46;
  const rows = [];
  const GR = new Map(grandchildGroups(tree).map((g) => [g.index, g]));
  const consumed = new Set();
  let y = 14, stemTop = null, lineKid = null, aboveThread = null;
  const src = tree.rows || [];
  src.forEach((r, ri) => {
    if (consumed.has(ri)) return;
    if (r.kind === "above") {
      const n = r.nodes[0];
      rows.push({ kind: "above", n, y: y + 12 });
      if (stemTop == null) stemTop = y + 12;
      if (tree.thread && n.id === tree.thread) aboveThread = y + 12;
      y += 40;
    } else if (r.kind === "couple") {
      rows.push({ kind: "couple", a: r.nodes[0], b: r.nodes[1] || null, y });
      if (stemTop == null) stemTop = y;
      y += 84;
    } else if (r.kind === "children") {
      /* the grandchildren row that belongs to this row: the next one before another children row */
      let gi = -1;
      for (let j = ri + 1; j < src.length && src[j].kind !== "children"; j++) if (src[j].kind === "grandchildren") { gi = j; break; }
      const G = gi >= 0 ? GR.get(gi) : null;
      if (G) consumed.add(gi);
      const under = new Map((G ? G.groups : []).map((g) => [g.parent, [...g.nodes]]));
      if (G && G.loose.length) {
        const fb = r.nodes.find((n) => tree.thread && n.id === tree.thread) || r.nodes[r.nodes.length - 1];
        under.set(fb, [...(under.get(fb) || []), ...G.loose]);
      }
      let yy = y + 10;
      const kids = r.nodes.map((n) => {
        const k = { n, y: yy, line: !!tree.thread && n.id === tree.thread, sub: [] };
        yy += 27;
        const gs = under.get(n) || [];
        if (gs.length) {
          k.sub = gs.map((g, j) => ({ n: g, y: k.y + 30 + j * 27 }));
          yy = k.sub[k.sub.length - 1].y + 30;
        }
        return k;
      });
      rows.push({ kind: "children", kids });
      const lk = kids.find((k) => k.line);
      if (lk) lineKid = lk;
      y = yy;
    } else if (r.kind === "grandchildren") {
      const g = r.nodes.map((n, i) => ({ n, y: y + 10 + i * 27 }));
      rows.push({ kind: "grand", g, from: y });
      y += 10 + r.nodes.length * 27;
    } else if (r.kind === "gap") {
      rows.push({ kind: "gap", text: r.text, y: y + 8 });
      y += 30;
    }
  });
  const H = y + (hasNext ? 30 : 8);
  const stemEnds = rows.filter((r) => r.kind !== "grand" && r.kind !== "gap")
    .flatMap((r) => (r.kind === "children" ? r.kids.map((k) => k.y) : [r.y + (r.kind === "couple" ? 64 : 0)]));
  const lastY = stemEnds.length ? Math.max(...stemEnds) : 0;
  const gaps = rows.filter((r) => r.kind === "gap");
  const kidsRow = rows.find((r) => r.kind === "children");
  const kidsTop = kidsRow ? kidsRow.kids[0].y - 10 : 0;
  return { W, H, X0, KX, rows, stemTop, lastY, gaps, kidsTop, lineKid, aboveThread };
}

/* ---- the map's text ---------------------------------------------------------------------------------------------- */
export function legText(L) {
  const from = L.a ? L.a.name : L.from, to = L.b ? L.b.name : L.to;
  return `${from} to ${to}${L.years ? ", " + L.years : ""}`;
}
