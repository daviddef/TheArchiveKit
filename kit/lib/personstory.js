/* The story layer of a person page (PERSON-PAGE-SPEC.md section 2a, ruled 4 November 2026): turns what an archive already holds about a person
   (the note, the places, the moves, the parent links) into what a reader scans first — a one-sentence lede, a journey, an ancestry thread,
   and short chapters laid on a timeline — without asking anyone to retype data.

   PURE FUNCTIONS, NO MARKUP, NO ARCHIVE NAMES, so node can test them (kit/tools/personstory_logic.mjs) and any archive's adapter can call them.
   THE LIVING RULE IS THE KIT'S: a relative is drawn through lib/person.js isLiving / isHeldOut (80 years; 60 for a child's parent). A living
   relative is a NAME and a RELATIONSHIP and nothing else: no dates, no place, no mark. Every person an archive names has a page (spec section 8,
   item 7), a living person's included, so the name still links to it; that page is the name, the relationships and the town and country. A relative the rule holds
   out is not drawn at all, not even as a «not yet found» card, because that card would say that someone is there.

   THE TREE SHAPE these functions read (an archive's adapter maps its own data into it; nothing here knows where it came from):
     byId[id] = { id, given, sur, sex, by, bye, dy, dye, bp, line, href, father, mother, kids[], spouse[], saidLiving? }
     by/dy are birth and death YEARS, bye/dye true when the year is an estimate, bp the birthplace, line a number (0 = this archive's own line),
     href the person's page (empty where there is none), father/mother/kids/spouse ids. */
import { isLiving, isHeldOut } from "./person.js";

const strip = (s) => String(s || "").replace(/\*\*(.+?)\*\*/g, "$1").replace(/(?<![*\w])\*(.+?)\*(?![*\w])/g, "$1")
  .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/\s+/g, " ").trim();

/* One plain sentence: the first bold lead of the note ("Generation 7 of the direct line — David's father."),
   else «rel», else nothing. Never cut mid-sentence: it is either the whole lead or it is absent. */
export function ledeOf(r) {
  const m = String(r.note || "").match(/^\s*\*\*(.+?)\*\*/);
  if (m) return strip(m[1]).replace(/[.\s]+$/, "") + ".";
  return r.rel ? r.rel[0].toUpperCase() + r.rel.slice(1) + "." : "";
}

const COUNTRY = { Zimbabwe: "ZW", "South Africa": "ZA", Australia: "AU", Croatia: "HR", Germany: "DE", Italy: "IT", Slovenia: "SI",
  Argentina: "AR", Uruguay: "UY", "United Kingdom": "GB", England: "GB", Scotland: "GB", Wales: "GB", Ireland: "IE", "United States": "US",
  "New Zealand": "NZ", Serbia: "RS", "Bosnia and Herzegovina": "BA", Austria: "AT", Hungary: "HU", France: "FR", Spain: "ES", Greece: "GR" };
const NAME_OF = Object.fromEntries(Object.entries(COUNTRY).map(([n, i]) => [i, n]));
export const flagOf = (iso) => iso && iso.length === 2 ? String.fromCodePoint(...[...iso.toUpperCase()].map((c) => 127397 + c.charCodeAt(0))) : "";

/* The stops of a life, in order. The row's `place` is «Senj → Harare → Johannesburg → Brisbane»; the first stop is the
   birth (year b), the last is the death when there is a death year; a middle stop takes its year from `moves`. `atlasPlaces`
   is atlas.json's list, used only to give a country to a stop that does not name one; a stop with no country anywhere has none, and none is guessed. */
export function journeyOf(r, atlasPlaces = [], gradeWords = {}) {
  const stops = String(r.place || "").split("→").map((s) => s.trim()).filter(Boolean);
  if (stops.length === 0) return [];
  const moves = r.moves || [];
  return stops.map((s, i) => {
    const name = s.split(",")[0].trim();
    const full = (r.places || []).find((p) => p.split(",")[0].trim() === name) || s;
    const bits = full.split(",").map((x) => x.trim());
    let country = bits.length > 1 ? bits[bits.length - 1] : "";
    if (!country) {
      const a = atlasPlaces.find((p) => p.name === name);
      country = a && a.country ? a.country : "";
    }
    const mv = moves.find((m) => m.place.split(",")[0].trim() === name);
    const first = i === 0, last = i === stops.length - 1 && stops.length > 1;
    const year = first ? r.b : last && r.d ? r.d : mv ? mv.y : null;
    return {
      name, iso: COUNTRY[country] || "", country,
      kind: first ? "Born" : last && r.d ? "Died" : "Moved", year: year ?? null,
      est: !!(mv && mv.est) || (first && !r.b && !!r.bEst), grade: mv ? mv.g : null,
    };
  });
}

/* The note, cut into chapters at every bold lead that opens a paragraph or a sentence. A chapter is {title, body};
   the grade word (*lore*, *doc*, *inf*) the author wrote at the end of a chapter is lifted into `grade`. A note with
   no bold lead is one chapter with no title. */
export function chaptersOf(note, lede = "") {
  const t = String(note || "").trim();
  if (!t) return [];
  const re = /(^|\n\n|(?<=[.!?»”] ))\*\*([^*]+?)\*\*/g;
  const hits = [...t.matchAll(re)].map((m) => ({ at: m.index + m[1].length, lead: m[2], end: m.index + m[0].length }));
  if (hits.length === 0) return [{ title: "", body: t, grade: gradeIn(t) }];
  const out = [];
  hits.forEach((h, i) => {
    const stop = i + 1 < hits.length ? hits[i + 1].at : t.length;
    let body = t.slice(h.end, stop).trim();
    let title = strip(h.lead).replace(/[.\s]+$/, "");
    // a lead that is a whole sentence (ends in a full stop) is the first line of the body, not a label
    const whole = /[.!?]\s*\*\*$/.test(t.slice(h.at, h.end)) && title.split(" ").length > 6;
    if (whole) { body = ("**" + h.lead + "** " + body).trim(); title = ""; }
    out.push({ title, body, grade: gradeIn(body) });
  });
  const pre = t.slice(0, hits[0].at).trim();
  if (pre) out.unshift({ title: "", body: pre, grade: gradeIn(pre) });
  // the lede already said the first lead; say it once
  const stem = lede.replace(/[.\s]+$/, "");
  if (stem && out[0] && !out[0].title && strip(out[0].body).startsWith(stem)) out[0].body = out[0].body.replace(/^\*\*.+?\*\*\s*/, "").trim();
  out.forEach((c) => { c.body = c.body.replace(/^[—–-]\s*/, "").trim(); });
  return out.filter((c) => c.title || c.body);
}

function gradeIn(s) {
  const m = String(s).match(/\*(lore|doc|inf|tree)\*/i);
  return m ? m[1].toLowerCase() : null;
}
export const GRADE_SAY = { doc: "Documented", inf: "Inferred", lore: "Family account", tree: "Family tree" };
export const wordsIn = (s) => strip(s).split(/\s+/).filter(Boolean).length;

/* The era a place was in, in a given year, as the Record Atlas's flag pages tell it: the flag, the polity, the pills (regime, leader, religion
   or ideology, each with its note), «Who & why» and «What it represents». The era is the one on the place's own country page that covers the
   year (Senj in 1951 is Croatia 1947–1990, the Socialist Republic of Croatia), because the Atlas's per-place flag timeline can file a
   neighbouring country's flag (the Yugoslav-era flag over Senj is filed under Serbia). Only where the country page has no era for that year
   does the slice's own flag stand. `eras` is site/src/data/flag-eras.json (scripts/build-flag-polities.py). Null where the Atlas has nothing:
   nothing is guessed. */
const slugOf = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
export function eraFlag(slice, eras, name, year) {
  if (!slice || !year) return null;
  const pl = slice.places.find((p) => p.n === name);
  if (!pl) return null;
  const own = slugOf(pl.cn) + "-flags--";
  let best = null;
  for (const [id, e] of Object.entries(eras || {})) {
    if (!id.startsWith(own) || !(e.from <= year && year <= e.to)) continue;
    if (!best || e.from > best[1].from) best = [id, e];
  }
  if (best) return card(best[0], best[1]);
  if (!pl.fl || !pl.fl.length) return null;
  let at = null;
  for (const [from, idx] of pl.fl) if (from <= year) at = idx;
  if (at === null) return null;
  const id = slice.fid[at], e = (eras || {})[id];
  if (e) return card(id, e);
  const [viewBox, inner] = slice.flags[at];
  return { viewBox, inner, dates: "", polity: "", id, pills: [], why: "", rep: "", caption: "" };
}
/* The Atlas writes an open span as «(1975–)». On a person's page that is also how a living person's birth is written, and the estate's gate for
   living years cannot tell them apart; «(from 1975)» says the same and is not mistaken. */
const openSpan = (t) => String(t ?? "").replace(/\((\d{3,4})\s?[–—-]\s?\)/g, "(from $1)");
const card = (id, e) => ({ viewBox: e.vb, inner: e.svg, dates: e.dates, polity: e.polity, id, pills: (e.pills || []).map((x) => ({ ...x, t: openSpan(x.t), tip: openSpan(x.tip) })), why: openSpan(e.why), rep: openSpan(e.rep), caption: e.caption || "" });

/* The mass-death events the Atlas dates and places at somewhere this person lived, in years they could have been there.
   A stop's window runs from the year they arrived to the year the next stop was reached. Where the next stop's year is not
   recorded (the move to Brisbane), the window runs on to the death year but only its first year is certain: an event that
   begins after that is marked `maybe` and the page says why. `events` is site/src/data/atlas-events.json. */
export function eventsAround(r, slice, events) {
  const stops = String(r.place || "").split("→").map((x) => x.trim().split(",")[0].trim()).filter(Boolean);
  if (!stops.length || !(r.b || r.bEst)) return [];
  const born = r.b || r.bEst, end = r.d || new Date().getFullYear();
  const moves = r.moves || [];
  const arrival = (i) => (i === 0 ? born : (moves.find((m) => m.place.split(",")[0].trim() === stops[i]) || {}).y ?? null);
  const found = new Map();
  stops.forEach((name, i) => {
    const pl = slice.places.find((p) => p.n === name);
    if (!pl) return;
    const from = arrival(i) ?? (i === stops.length - 1 ? end : null);
    if (from === null) return;
    const next = i + 1 < stops.length ? arrival(i + 1) : null;
    const to = i === stops.length - 1 ? end : (next ?? end);
    const certainTo = i === stops.length - 1 ? end : (next ?? from);
    for (const id of pl.ev || []) {
      const e = events[id];
      if (!e || e.to < from || e.from > to) continue;
      const maybe = e.from > certainTo;
      const cur = found.get(id) || { id, ...e, where: [], maybe: true };
      cur.where.push({ name, maybe });
      cur.maybe = cur.maybe && maybe;
      found.set(id, cur);
    }
  });
  return [...found.values()].sort((a, b) => a.from - b.from);
}

/* The Flag Atlas page for a flag id such as «serbia-flags--era-1944»: the country's page, at that era. */
export function flagUrl(id) {
  const m = String(id || "").match(/^(.+?)--(.+)$/);
  return m ? `https://recordatlas.org/flags/${m[1]}/#${m[2]}` : id ? `https://recordatlas.org/flags/${id}/` : "";
}

/* The page for a place: this archive's own page where it has one (/places/<slug>/), else the place's page in the Record Atlas
   (the id the Roots & Routes slice already carries), else nothing: a link is made only where there is somewhere to go. */
export function placeHref(name, archivePlaces, slice, u = (x) => x) {
  const own = (archivePlaces || []).find((p) => p.name === name);
  if (own) return { href: u(`/places/${own.slug}/`), where: "this archive" };
  const pl = slice && (slice.places || []).find((p) => p.n === name);
  return pl && pl.id ? { href: `https://recordatlas.org/place/${pl.id}/`, where: "Record Atlas" } : null;
}

/* ONE SENTENCE FOR THE SHAPE OF A LIFE, from the stops alone: where they were born, where they died, and the places between. Neutral about the
   person (no pronoun), and it says only what the journey holds: «Born at Senj in 1951 and died at Brisbane in 2026, by way of Harare and
   Johannesburg.» Empty when there is no birth year. */
export function lifeSentence(journey, r) {
  const born = journey.find((s) => s.kind === "Born"), died = journey.find((s) => s.kind === "Died");
  if (!born || !r.b) return "";
  const mids = journey.filter((s) => s.kind === "Moved").map((s) => s.name);
  const list = (a) => (a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]);
  let t = `Born at ${born.name} in ${r.b}`;
  if (died && r.d) t += ` and died at ${died.name} in ${r.d}`;
  if (mids.length) t += (died && r.d ? ", by way of " : ", and later at ") + list(mids);
  return t + ".";
}

/* WHAT THE ARCHIVE CANNOT ACCOUNT FOR, from the journey: a stop whose year is only the family's account or is approximate, a stop with no year,
   a last place whose arrival is not recorded. Each is one paragraph of markdown for a card in the life; `extra` are paragraphs the archive has
   written for this person (a conflict between two of its own sources). Nothing is added that the stops do not hold. Empty when there is nothing
   to say. */
export function gapsOf(journey, extra = [], here = "", help = "") {
  const out = [];
  journey.forEach((s, i) => {
    if (s.kind === "Born") return;
    const when = s.year ? `${s.est ? "about " : ""}${s.year}` : "no year";
    if (!s.year) out.push(`**${s.name}, ${when}.** The place is in the family's account; no year is recorded for it.`);
    else if (s.kind === "Moved" && (s.grade === "lore" || s.est))
      out.push(`**${s.name}, ${when}.** This is the family's account and nothing more: no document has been found for it, and the year is approximate.`);
    else if (s.kind === "Died" && !s.grade && journey.length > 2 && journey[i - 1] && journey[i - 1].kind === "Moved")
      out.push(`**${s.name}, arrival.** The death is recorded; the year of arriving there is not.`);
  });
  const all = [...out, ...extra];
  if (!all.length) return "";
  if (help) all.push(help);
  return all.join("\n\n") + `\n\nWhere to look is under [Where they lived, and what is still missing](${here}#where): the registers and archives the Record Atlas lists for each of these places.`;
}

/* The one-line reading of a lore claim: the bold sentence its page («against») leads with. */
export const leadOf = (t) => { const m = String(t || "").match(/\*\*(.+?)\*\*/s); return m ? m[1].replace(/\*/g, "").trim() : ""; };

/* THE KIT'S LIVING RULE APPLIED TO A TREE PERSON. The rule reads a canonical person; a tree row is mapped to one here: the birth and death
   years, the youngest child's birth year (an undated parent of a recent child is living), and whether a parent is living (an undated child of
   a living parent is held out). `rule` is {now, sources, heldIds}. */
const kidsCache = new WeakMap();
function kidsOf(byId, id) {
  let idx = kidsCache.get(byId);
  if (!idx) {
    idx = new Map();
    for (const x of Object.values(byId)) for (const par of [x.father, x.mother]) if (par) (idx.get(par) || idx.set(par, new Set()).get(par)).add(x.id);
    kidsCache.set(byId, idx);
  }
  return [...new Set([...(byId[id]?.kids || []), ...(idx.get(id) || [])])];
}
function canon(byId, q) {
  const kidYears = kidsOf(byId, q.id).map((k) => byId[k]?.by).filter(Boolean);
  return { id: q.id, born: q.by || null, died: q.dy || null, dead: q.dead === true, saidLiving: q.saidLiving === true,
           youngestChildYear: kidYears.length ? Math.max(...kidYears) : null };
}
export function livingOf(byId, id, rule = {}) {
  const q = byId[id];
  return Boolean(q) && isLiving(canon(byId, q), rule);
}
export function heldOutOf(byId, id, rule = {}) {
  const q = byId[id];
  if (!q) return false;
  const parentLiving = [q.father, q.mother].some((par) => par && byId[par] && isLiving(canon(byId, byId[par]), rule));
  return isHeldOut(canon(byId, q), { ...rule, parentLiving });
}

/* One person as a card: name, years, birthplace, a link to their page where this archive has one. A person the records do not name is an
   «unknown» node. A LIVING person (the kit's rule) is a name and a relationship and nothing else: no dates, no place, no mark; the name links to
   their own page, which is itself only a name, relationships and a town and country. A person the
   rule HOLDS OUT comes back as null: the caller leaves them out, and nothing says they exist. */
export function famNode(byId, id, rel, missing, rule = {}) {
  const q = id && byId[id];
  if (!q) return { unknown: true, rel, missing };
  if (heldOutOf(byId, id, rule)) return null;
  const living = livingOf(byId, id, rule);
  const y = (v, est) => (v ? (est ? "c. " : "") + v : "");
  const dates = living ? "" : [y(q.by, q.bye), q.dy ? y(q.dy, q.dye) : ""].filter(Boolean).join(" – ");
  return {
    id: q.id, rel, line: q.line, living,
    name: [q.given, q.sur].filter(Boolean).join(" "),
    dates: dates && !q.dy && q.by && !living ? dates + " –" : dates,
    place: living ? "" : q.bp || "", sex: q.sex,
    href: q.href || "",
  };
}

/* The family of one person, three generations deep, from the parent links the archive's own people data (the same data Roots & Routes
   draws) states: their grandparents, parents, spouse, brothers and sisters, and children. A parent the records do not name is returned as
   an «unknown» node, so the gap is drawn rather than hidden. Living relatives are names only and held-out relatives are absent (famNode); a link is
   made only to a person page this archive has (`href`). */
export function familyOf(byId, pid, rule = {}) {
  const p = byId[pid];
  if (!p) return null;
  const node = (id, rel, missing) => famNode(byId, id, rel, missing, rule);
  const some = (list) => list.filter(Boolean);
  const fa = byId[p.father], mo = byId[p.mother];
  const parents = some([node(p.father, "Father", "Father not yet found"), node(p.mother, "Mother", "Mother not yet found")]);
  const grand = some([
    node(fa && fa.father, "Father's father", "Not yet found"), node(fa && fa.mother, "Father's mother", "Not yet found"),
    node(mo && mo.father, "Mother's father", "Not yet found"), node(mo && mo.mother, "Mother's mother", "Not yet found"),
  ]);
  // children are found from the parent links on each person (the same way Roots & Routes finds them), not from a list on the parent
  const sibIds = new Set();
  for (const id of [p.father, p.mother]) if (id && byId[id]) for (const k of kidsOf(byId, id)) if (k !== pid) sibIds.add(k);
  const byBirth = (a, b) => (byId[a].by || 9999) - (byId[b].by || 9999);
  return {
    self: node(pid, "This person"),
    spouses: some((p.spouse || []).filter((id) => byId[id]).map((id) => node(id, "Married to"))),
    parents, grand, hasGrand: Boolean(fa || mo) && grand.some((g) => !g.unknown),
    siblings: some([...sibIds].filter((id) => byId[id]).sort(byBirth).map((id) => node(id, "Brother or sister"))),
    children: some(kidsOf(byId, pid).filter((id) => byId[id]).sort(byBirth).map((id) => node(id, "Child"))),
  };
}

/* WHERE THEY CAME FROM, AS A THREAD. For each parent, climb the father's line (the line the surname travels) as far up as the people data
   goes. Each thread is the parent, the generations between (kept as names, not cards: a dotted gap), and the earliest person the archive
   holds on that line. «origin» is the family's own account of where the line began, when there is one and the earliest person is on the
   archive's own line: it is drawn above the earliest, with a dotted gap that says plainly no record yet joins them. A thread of one (a
   parent nobody above is known for) is drawn as just that parent, with the gap said. */
export function ancestryOf(byId, pid, origin = null, rule = {}) {
  const p = byId[pid];
  if (!p) return [];
  const threads = [];
  for (const [side, id] of [["Father's line", p.father], ["Mother's line", p.mother]]) {
    const chain = [], seen = new Set([pid]);
    for (let q = id; q && byId[q] && !seen.has(q); q = byId[q].father) { seen.add(q); chain.push(q); }
    const nodes = chain.map((c, i) => famNode(byId, c, i === 0 ? (side === "Father's line" ? "Father" : "Mother") : "", "", rule));
    if (!nodes.length || nodes.some((n) => n === null)) { threads.push({ side, parent: famNode(byId, null, side === "Father's line" ? "Father" : "Mother", `${side === "Father's line" ? "Father" : "Mother"} not yet found`, rule), between: [], earliest: null, origin: null }); continue; }
    // the grandparents are drawn on their own row, so the line above starts beyond them: parent [0], grandfather [1], then the rest
    const earliest = nodes.length > 2 ? { ...nodes[nodes.length - 1], rel: "The earliest we can document" } : null;
    const between = nodes.length > 3 ? nodes.slice(2, -1).reverse() : [];
    threads.push({
      side, parent: nodes[0], between, earliest,
      origin: earliest && earliest.line === 0 && origin ? origin : null,
    });
  }
  return threads;
}

/* A story is worth a page of its own (story mode) only when it holds something beyond the first stop saying nobody is named. */
export const hasStory = (stages) => (stages || []).some((s) => !(s.key === "origin" && s.empty));

/* THE STORY, IN THE ORDER A LIFE HAPPENS.
   The roster note is cut into chapters (chaptersOf) in the order the researcher wrote them, which is the order they were found, not the order
   they happened. This lays them on a timeline: where the person came from (their parents and grandparents, from the family data), their
   birth, their life (by the year each chapter names, else where it stood), their death, what they left behind (their children, from the family
   data), and last the notes about the record itself (why the archive holds this person, how a name was matched), which are about the archive
   and not about the life. Nothing is written here that the data does not hold: a stage with nothing in it is not drawn, and the words are
   neutral about the person (no pronoun is guessed). A chapter is placed by its title, or by its words where it has no title; the rules are
   the three regular expressions below. */
/* A chapter that is about the ARCHIVE and not the life (why a person is held, how a name was matched) goes last and quiet. The default is the
   words every archive uses; an archive adds its own through `storyOf(..., { metaRx })`. */
export const META = /this list|the list|this archive|the archive|index entry|matched/i;
const BIRTH = /^(born|birth|baptis|christen)|\b(born|birth|baptis|christen)/i;
const DEATH = /^(died|death|buried|burial|grave|funeral|killed|lost)|\b(died|death|buried|burial|funeral)\b/i;
const LEGACY = /\b(legacy|left behind|remembered|memorial|descendants|inherit)/i;
/* a chapter that reads an entry off a register: «read on the page», «read off the register», a page and entry number */
const REGISTER = /\bread (on the page|off the register|at level|at full)|\bpage \d+,? entry \d+|\bentry \d+, image \d+/i;
const yearOf = (s) => { const m = String(s || "").match(/\b(1[5-9]\d\d|20[0-2]\d)\b/); return m ? +m[1] : null; };
const firstSentence = (t) => { const m = String(t).match(/^(.+?[.!?»”])(\s+|$)/s); return m ? [m[1], String(t).slice(m[0].length)] : [t, ""]; };

export function storyOf(chapters, fam, journey = [], r = {}, threads = [], { metaRx = META } = {}) {
  const buckets = { birth: [], life: [], death: [], legacy: [], about: [] };
  for (const c of chapters || []) {
    const t = c.title || "";
    let ph;
    if (t) ph = BIRTH.test(t.slice(0, 48)) ? "birth" : DEATH.test(t.slice(0, 48)) ? "death" : LEGACY.test(t) ? "legacy" : "life";
    else {
      const body = strip(c.body);
      // an untitled opening that starts «Died in 2026. …»: the first sentence is the death, the rest is usually the archive talking
      const m = body.match(/^(Died|Born)\b/);
      if (m) {
        const [first, rest] = firstSentence(c.body.replace(/^\*\*(.+?)\*\*/, "$1"));
        buckets[m[1] === "Died" ? "death" : "birth"].push({ title: "", body: first, grade: c.grade, year: yearOf(first) });
        if (strip(rest)) buckets[metaRx.test(strip(rest)) ? "about" : "life"].push({ title: "", body: rest.trim(), grade: c.grade, year: yearOf(rest) });
        continue;
      }
      ph = metaRx.test(body) ? "about" : "life";
    }
    buckets[ph].push({ title: t, body: c.body, grade: c.grade, reg: REGISTER.test(strip(c.body)), year: yearOf(t) || yearOf(strip(c.body)) });
  }
  // the life, in the order it happened: by the year a chapter names; a chapter that names none keeps its place after the one before it
  let carry = 0;
  const life = buckets.life.map((c, i) => { carry = c.year ?? carry; return { ...c, _k: carry, _i: i }; })
    .sort((a, b) => a._k - b._k || a._i - b._i);

  const people = (list) => list.filter((n) => !n.unknown).map((n) => ({ name: n.name, dates: n.dates, place: n.place, href: n.href, rel: n.rel, external: n.external, site: n.site }));
  const born = r.b || r.bEst, died = r.d;
  const stages = [];
  const known = (list) => list.some((n) => !n.unknown);
  /* The first stop is ALWAYS drawn: it carries the anchor #family, and the spec requires a Family on every page that is not living. When no
     parent is named it says so (`empty`), rather than dropping the stop, because a missing section is a claim made in silence. */
  const hasOrigin = threads.some((t) => t.earliest) || (fam && (known(fam.parents) || (fam.hasGrand && known(fam.grand))));
  stages.push({ key: "origin", label: "Where they came from", when: "", empty: !hasOrigin, threads: threads.filter((t) => t.earliest),
    grand: fam && fam.hasGrand ? fam.grand : [], parents: fam ? fam.parents : [], cards: [] });
  const sibs = fam ? people(fam.siblings) : [];
  if (buckets.birth.length || sibs.length) stages.push({ key: "birth", label: "Birth", when: born ? String(born) : "", people: sibs, plabel: "Brothers and sisters", cards: buckets.birth });
  if (life.length) stages.push({ key: "life", label: "Life", when: born && died ? `${born} – ${died}` : "", cards: life });
  if (buckets.death.length) stages.push({ key: "death", label: "Death", when: died ? String(died) : "", cards: buckets.death });
  const kids = fam ? people(fam.children) : [];
  if (kids.length || buckets.legacy.length) stages.push({ key: "legacy", label: "What they left behind", when: "", people: kids, plabel: "Children", cards: buckets.legacy });
  if (buckets.about.length) stages.push({ key: "about", label: "About this record", when: "", cards: buckets.about, quiet: true });
  return stages;
}
