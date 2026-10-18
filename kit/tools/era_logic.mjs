// node kit/tools/era_logic.mjs : the "at the time" note's library (lib/era.js) held to the shared cases (kit/data/era-cases.json),
// the markup the component draws (components/EraNote.astro) held to what the gate reads, and the gate (checkera.py) shown to accept
// what the library draws and to fail when the page is changed. The Python half of the library (eralib.py) is held to the SAME cases
// by era_selftest.py, so the two cannot drift apart.
import fs from "fs"; import os from "os"; import path from "path"; import { fileURLToPath, pathToFileURL } from "url";
import { spawnSync } from "child_process";
import * as E from "../lib/era.js";
import * as R from "../lib/rec.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const FIX = JSON.parse(fs.readFileSync(path.join(kit, "data", "era-cases.json"), "utf8"));
let bad = 0, n = 0;
const ok = (label, cond, detail) => { n++; if (!cond) { bad++; console.log("  FAIL  " + label + (detail ? "\n         " + detail : "")); } else console.log("  ok    " + label); };
const sub = (got, want) => Object.entries(want).every(([k, v]) => got != null && got[k] === v);
const snapFor = (c) => c.snap === "none" ? null : c.snap ? FIX.other_snapshots[c.snap] : FIX.snapshot;

/* the cases, run against a library (the real one, or a copy with one rule broken) -> the ids of the cases that fail */
function failing(lib) {
  const out = [];
  for (const c of FIX.cases) {
    const snap = JSON.parse(JSON.stringify(snapFor(c)));
    let got, why, threw = null;
    const o = c.opts ? { recentFrom: c.opts.recent_from } : undefined;
    try { got = lib.eraAt(snap, c.place, c.year, o); why = lib.whyNot(snap, c.place, c.year, o); } catch (e) { threw = e.message; }
    const pass = threw === null && why === c.why && (c.want === null ? got === null : sub(got, c.want));
    if (!pass) out.push(c.id);
  }
  for (const [s, want] of FIX.fold) { let g; try { g = lib.fold(s); } catch (e) { g = "threw"; } if (g !== want) out.push("fold:" + s); }
  for (const [d, y, want] of FIX.years) { let g; try { g = lib.plainYear(d, y); } catch (e) { g = "threw"; } if (g !== want) out.push("year:" + d + "|" + y); }
  for (const h of FIX.href_cases) {
    const snap = { atlas: { base: h.base } }; let g; try { g = lib.regionHref(snap, "ruritania"); } catch (e) { g = "threw"; }
    if (g !== h.href) out.push(h.id);
  }
  /* rule m: who reigned. The region-level cases (rulerAt and whyNoRuler) and the note-level cases (eraAt's ruler) */
  for (const c of FIX.ruler_cases) {
    const snap = JSON.parse(JSON.stringify(FIX.other_snapshots[c.snap])); let got, why, threw = null;
    try { got = lib.rulerAt(snap, c.region, c.year); why = lib.whyNoRuler(snap, c.region, c.year); } catch (e) { threw = e.message; }
    if (!(threw === null && why === c.why && (c.name === null ? got === null : got !== null && got.name === c.name))) out.push(c.id);
  }
  for (const c of FIX.ruler_note_cases) {
    const snap = JSON.parse(JSON.stringify(FIX.other_snapshots[c.snap])); let got, threw = null;
    try { got = lib.eraAt(snap, c.place, c.year); } catch (e) { threw = e.message; }
    if (!(threw === null && (got !== null) === c.era && (!c.era || ((got.ruler ? got.ruler.name : null) === c.ruler && got.boundary === c.boundary)))) out.push(c.id);
  }
  {
    const rs = JSON.parse(JSON.stringify(FIX.other_snapshots.rulers));
    const f = lib.rulerAt(rs, "rulerland", 1836), q = lib.rulerAt(rs, "rulerland", 1745);
    if (!(f && f.polityId === "union-of-the-two-realms" && f.from === "1830" && f.to === "1859" && f.fromYear === 1830 && f.toYear === 1859 && f.q === null && q && q.q === "Q1")) out.push("ruler:fields");
  }
  // the words a reader gets
  const era = lib.eraAt(JSON.parse(JSON.stringify(FIX.snapshot)), "Hentzau", 1750);
  const html = lib.renderEra(era);
  if (!(html.startsWith('<span class="era-note" data-era="ruritania--era-1700" data-era-year="1750" data-era-assessed="1" data-era-place="hentzau"><span class="era-pre">· At the time: </span>') && html.includes('<span class="era-lab">Kingdom of Ruritania</span>')
        && html.includes('<a class="era-src" href="https://atlas.example.test/region/ruritania/#era-1700" rel="noopener">per the Record Atlas</a>') && !html.includes("data-era-boundary"))) out.push("render:note");
  const bnd = lib.renderEra(lib.eraAt(JSON.parse(JSON.stringify(FIX.snapshot)), "Hentzau", 1850));
  if (!(bnd.includes(' data-era-boundary="1"') && bnd.includes('<span class="era-pre">· From that year: </span>') && bnd.includes('data-era="ruritania--era-1850"'))) out.push("render:boundary");
  if (lib.renderEra(null) !== "") out.push("render:null-is-empty");
  const edgeHtml = lib.renderEra(lib.eraAt(JSON.parse(JSON.stringify(FIX.snapshot)), "Edge Agree Town", 1750));
  if (!edgeHtml.includes(' data-era-assessed="1" data-era-edge-agree="1" data-era-place="edge agree town">') || html.includes("data-era-edge-agree")) out.push("render:edge-agree");
  const unas = lib.renderEra(lib.eraAt(JSON.parse(JSON.stringify(FIX.other_snapshots.allow)), "Null Town", 1750));
  if (!unas.includes(' data-era-assessed="0"')) out.push("render:unassessed");
  const mar = lib.renderEra(lib.eraAt(JSON.parse(JSON.stringify(FIX.other_snapshots.margin)), "Calabrio", 1830));
  const con = lib.renderEra(lib.eraAt(JSON.parse(JSON.stringify(FIX.other_snapshots.margin)), "Scopetown", 1825));
  if (!(mar.includes(' data-era-assessed="1" data-era-approx="1" data-era-place=') && !mar.includes("data-era-contested") && con.includes(' data-era-assessed="1" data-era-contested="1" data-era-place=') && !con.includes("data-era-approx") && !html.includes("data-era-approx") && !html.includes("data-era-contested"))) out.push("render:margin-marks");
  /* the words claim no more than the Atlas does: the regime label and the source, no bound of the era, no digit but the event year's */
  const words = (h) => h.replace(/<[^>]*>/g, "");
  if (!(words(mar) === "· At the time: Kingdom of the Two Realms per the Record Atlas" && words(con) === "· At the time: Realm of the Seven Seats per the Record Atlas")) out.push("render:margin-words");
  const soft = lib.renderEra(lib.eraAt(JSON.parse(JSON.stringify(FIX.other_snapshots.margin)), "Softton", 1711));
  if (!(soft.includes(' data-era-margin-unsourced="1"') && !mar.includes("margin-unsourced") && !html.includes("margin-unsourced"))) out.push("render:margin-marks");
  /* rule m in the markup: off unless the archive asks, the Atlas's name exactly and escaped, no ruler on a boundary note */
  {
    const rs = () => JSON.parse(JSON.stringify(FIX.other_snapshots.rulers));
    const er = lib.eraAt(rs(), "Rulertown", 1745);
    const off = lib.renderEra(er), on = lib.renderEra(er, { rulers: true }), onFalse = lib.renderEra(er, { rulers: "yes" });
    if (/era-ruler/.test(off) || /era-ruler/.test(onFalse) || off.replace(/<[^>]*>/g, "") !== "· At the time: Kingdom of Ruritania per the Record Atlas") out.push("render:ruler-off");
    if (!(on.includes(' data-era-place="rulertown" data-era-ruler="Rudolf II">') && on.includes('<span class="era-lab">Kingdom of Ruritania</span> <span class="era-ruler">(Rudolf II)</span> <a class="era-src" href=')
          && on.replace(/<[^>]*>/g, "") === "· At the time: Kingdom of Ruritania (Rudolf II) per the Record Atlas")) out.push("render:ruler");
    const ex = lib.renderEra(lib.eraAt(rs(), "Rulertown", 1888), { rulers: true });
    if (!(ex.includes('data-era-ruler="Stefan I &amp; Ana (listed as Štefan II)"') && ex.includes('<span class="era-ruler">(Stefan I &amp; Ana (listed as Štefan II))</span>'))) out.push("render:ruler-escapes");
    const bn = lib.renderEra(lib.eraAt(rs(), "Tidy Town", 1800), { rulers: true });
    if (/era-ruler/.test(bn) || !bn.includes("data-era-boundary")) out.push("render:ruler-boundary");
    const ed = lib.renderEra(lib.eraAt(rs(), "Rulerborder Town", 1750), { rulers: true });
    if (/era-ruler/.test(ed) || !ed.includes("data-era-edge-agree")) out.push("render:ruler-edge");
  }
  const seeded = lib.eraAt(JSON.parse(JSON.stringify(FIX.snapshot)), "Zenda", 1975);
  if (!lib.renderEra(seeded).includes("per this archive's own research</a>")) out.push("render:seeded-words");
  const e = lib.renderEra({ id: 'x--1"', label: "<script>alert(1)</script> & \"q\"", year: 1750, source: "<b>", href: 'https://a.example.test/"x' });
  if (/<script|<b>|\sx=|href="https:\/\/a\.example\.test\/"x/.test(e) || !e.includes("&lt;script&gt;") || !e.includes("&amp;") || !e.includes("&quot;")) out.push("render:escapes");
  return out;
}

const real = failing(E);
ok("the shared cases all hold (" + (FIX.cases.length + FIX.fold.length + FIX.years.length + FIX.href_cases.length) + " cases and the markup checks)", real.length === 0, real.join(", "));

// planted faults: a copy of era.js with one rule broken must fail the case that guards it
const src = fs.readFileSync(path.join(kit, "lib", "era.js"), "utf8");
const IFC = 'if (covering.length > 1 || refused.length > 0 || covering.some((e) => eras.some((o) => o !== e && numeric(o) && meets(e, o)))) return no("contested");';
const faults = [
  ["the end year of an era is inside it (closed interval)", "(e.to === null || year < e.to)", "(e.to === null || year <= e.to)", "the-year-an-era-ends-belongs-to-the-next-era"],
  ["a still-running era covers nothing", "(e.to === null || year < e.to)", "year < e.to", "accents-and-case-are-folded"],
  ["a boundary year takes the newer era whatever the snapshot says", "if (pol.boundary !== \"newer\") return no(\"boundary\");", "", "a-boundary-year-is-silent-when-the-snapshot-does-not-say-newer"],
  ["a boundary year is not noticed", "if (year === e.from && hasPredecessor(snap, region, eras, e)) {", "if (false && hasPredecessor(snap, region, eras, e)) {", "a-boundary-year-takes-the-newer-era-and-says-so"],
  ["a refused predecessor does not make a boundary", "return (snap.dropped || []).some((d) => dropOk(d) && d.region === region && d.to === e.from);", "return false;", "a-boundary-after-a-refused-era-still-says-so"],
  ["the first year after a gap is taken for a boundary", "numeric(o) && o.to === e.from", "numeric(o) && o.to !== null && o.to <= e.from", "the-first-year-after-a-gap-is-not-a-boundary"],
  ["the quiet rule is off", "if (e.to === null && year >= recentFrom) return no(\"recent\");", "", "the-quiet-rule-1990"],
  ["the quiet rule starts a year late", "year >= recentFrom) return no(\"recent\")", "year > recentFrom) return no(\"recent\")", "the-quiet-rule-1990"],
  ["the quiet rule touches closed eras", "if (e.to === null && year >= recentFrom)", "if (year >= recentFrom)", "the-quiet-rule-never-touches-a-closed-era"],
  ["the caller's quiet-rule year is ignored", "opts && opts.recentFrom !== undefined ? opts.recentFrom : (isYear(pol.recent_from) ? pol.recent_from : RECENT_FROM)", "(isYear(pol.recent_from) ? pol.recent_from : RECENT_FROM)", "the-quiet-rule-can-be-moved-by-the-caller"],
  ["the snapshot's quiet-rule year is ignored", "(isYear(pol.recent_from) ? pol.recent_from : RECENT_FROM)", "RECENT_FROM", "the-quiet-rule-can-be-moved-by-the-snapshot"],
  ["null is taken for false", "v === null || v === undefined ? \"unassessed\"", "v === null || v === undefined ? \"no\"", "an-era-with-null-flags-is-unassessed"],
  ["an unassessed era is noted whatever the policy says", "if (unassessed && pol.unassessed !== \"allow\") return no(\"unassessed\");", "", "an-era-with-null-flags-is-unassessed"],
  ["an unassessed era is never allowed", "if (unassessed && pol.unassessed !== \"allow\")", "if (unassessed)", "an-era-with-null-flags-is-allowed-when-the-snapshot-says-so"],
  ["a flag that is neither true, false nor null counts as false", ": v === null || v === undefined ? \"unassessed\" : \"yes\")", ": v === null || v === undefined ? \"unassessed\" : \"no\")", "a-flag-that-is-neither-true-false-nor-null-is-silent-even-when-allowing"],
  ["an approximate era is noted under the refuse policy", "if (ap === \"yes\" && pol.approx !== \"margin\") return \"approx\";", "", "margin-approx-refuse-policy-refuses-an-approx-era"],
  ["an approximate era with no margin gets a note", "&& !(isMargin(e.from_margin) && (e.to === null || isMargin(e.to_margin)))) return ap === \"yes\" ? \"approx\" : \"contested\";", "&& false) return null;", "margin-a-flagged-era-with-an-unknown-end-margin-is-silent"],
  ["a contested era is noted under the refuse policy", "if (cp !== \"scope\" && cp !== \"margin\") return \"contested\";", "", "margin-contested-refuse-policy-refuses-a-bounds-scope-era"],
  ["a regime scope on an unflagged era is used", "if (e.contested_scope === \"regime\" || e.contested_scope === \"part\") return \"contested\";", "", "margin-a-regime-scope-on-an-era-that-is-not-flagged-contested-is-still-silent"],
  ["a contested era of an unknown scope is noted", "if (e.contested_scope !== \"bounds\" && e.contested_scope !== \"none\" && !(", "if (false && !(", "margin-an-unknown-scope-on-a-contested-era-is-silent"],
  ["a contested era of scope none is refused", " && e.contested_scope !== \"none\" && !(", " && !(", "margin-a-contested-era-of-scope-none-is-used"],
  ["the floor is not applied", "Math.max(n, m)", "m", "margin-margin-0-from-the-atlas-the-floor-still-holds-1805"],
  ["an unsourced margin is not softer", "+ (soft ? n : 0)", "+ 0", "margin-an-unsourced-margin-of-2-1711-is-allowed-and-says-it-rests-on-an-unsourced-margin"],
  ["the snapshot's floor is ignored", "isMargin(pol.margin_years) ? pol.margin_years : MARGIN_YEARS", "MARGIN_YEARS", "margin-margin-0-and-a-floor-of-0-is-a-clean-date-1800"],
  ["the unsourced mark is not carried on the era", "unsourced: e.margin_sourced === false &&", "unsourced: false &&", "margin-an-unsourced-margin-of-2-1711-is-allowed-and-says-it-rests-on-an-unsourced-margin"],
  ["the unsourced mark is not drawn", "${era.unsourced === true ? ' data-era-margin-unsourced=\"1\"' : \"\"}", "", "render:margin-marks"],
  ["a contested era with no scope is noted under the scope policy", "(e.contested_scope === null || e.contested_scope === undefined) && cp === \"margin\"", "(e.contested_scope === null || e.contested_scope === undefined)", "margin-contested-with-no-scope-is-silent-under-the-scope-policy"],
  ["a contested era with no scope is never noted", "(e.contested_scope === null || e.contested_scope === undefined) && cp === \"margin\"", "false", "margin-contested-with-no-scope-is-allowed-10-years-inside-under-the-margin-policy"],
  ["the start margin is not applied", "return year >= span.first && (span.last === null || year <= span.last) ? null : \"margin\";", "return (span.last === null || year <= span.last) ? null : \"margin\";", "margin-approx-1820-is-5-years-from-the-start-so-silent"],
  ["the end margin is not applied", "return year >= span.first && (span.last === null || year <= span.last) ? null : \"margin\";", "return year >= span.first ? null : \"margin\";", "margin-approx-1856-is-5-years-from-the-end-so-silent"],
  ["a year AT the margin is allowed (at least, not more than)", "first: e.from + (rf !== null && rf > 0 ? rf + 1 : 0)", "first: e.from + (rf !== null ? rf : 0)", "margin-approx-1820-is-5-years-from-the-start-so-silent"],
  ["the end margin counts a year too few", "last: e.to === null ? null : e.to - 1 - (rt !== null ? rt : 0)", "last: e.to === null ? null : e.to - (rt !== null ? rt : 0)", "margin-approx-1856-is-5-years-from-the-end-so-silent"],
  ["a margin of 0 is silent in the first year", "first: e.from + (rf !== null && rf > 0 ? rf + 1 : 0)", "first: e.from + (rf !== null ? rf + 1 : 0)", "margin-margin-0-and-a-floor-of-0-is-a-clean-date-1800"],
  ["an unflagged era's own margin is ignored", "if (!ap && !co && rf === null && rt === null) return null;", "if (!ap && !co) return null;", "margin-an-unflagged-era-keeps-the-margin-the-contract-gives-it-1705"],
  ["the recorded decision is not held to the margins", "if (r == null || typeof r !== \"object\" || r.kind !== span.kind || r.first !== span.first || r.last !== span.last) return \"bad-margin\";", "", "margin-a-recorded-decision-that-does-not-follow-the-margins-is-silent"],
  ["a missing record is accepted", "if (r == null || typeof r !== \"object\" ||", "if (r != null && (typeof r !== \"object\") ||", "margin-a-flagged-era-with-no-recorded-decision-is-silent"],
  ["the approx mark is not carried on the era", "approx: flag(e.approx) === \"yes\",", "approx: false,", "margin-approx-1830-in-1815-1861-keeps-its-note"],
  ["the contested mark is not carried on the era", "contested: flag(e.contested) === \"yes\", unsourced", "contested: false, unsourced", "margin-contested-bounds-1822-is-allowed-under-scope-bounds"],
  ["an era that overlaps another is not contested", "covering.some((e) => eras.some((o) => o !== e && numeric(o) && meets(e, o)))", "false", "an-era-that-overlaps-another-is-silent-even-where-it-stands-alone"],
  ["a year inside two eras gets a note", IFC, "", "a-year-inside-two-overlapping-eras-is-silent"],
  ["a refused era overlapping a kept one is ignored", "covering.length > 1 || refused.length > 0 ||", "covering.length > 1 ||", "a-refused-era-overlapping-a-kept-one-is-silent"],
  ["an empty label is allowed", "if (!label(e)) return no(\"no-label\");", "", "an-empty-regime-label-is-silent"],
  ["an era whose id is not the contract's is allowed", "if (e.id !== eraId(region, e.from)) return no(\"bad-id\");", "", "an-era-whose-id-is-not-the-contracts-is-silent"],
  ["any url is a link", "return e.url === `/region/${region}/#era-${e.from}` ? b + e.url : null;", "return b + e.url;", "an-era-keeps-the-link-the-contract-gives-only-if-it-is-its-own"],
  ["a place is not folded for case", ".toLowerCase().replace(/['’`]/g, \"\")", ".replace(/['’`]/g, \"\")", "accents-and-case-are-folded"],
  ["a place is not folded for accents", ".normalize(\"NFKD\").replace(/[̀-ͯ]/g, \"\")", "", "accents-and-case-are-folded"],
  ["a string year is accepted", "Number.isInteger(n) && n >= 1 && n <= 9999", "Number(n) >= 1", "a-string-year-is-refused"],
  ["a fractional year is accepted", "Number.isInteger(n) && n >= 1 && n <= 9999", "n >= 1 && n <= 9999", "a-fractional-year-is-refused"],
  ["a words-only end year is an era", "(e.to === null || (isYear(e.to) && e.from < e.to))", "(e.to === null || e.to === \"present\" || (isYear(e.to) && e.from < e.to))", "an-era-with-a-words-only-end-is-not-an-era",
    [["export const covers = (e, year) => e.from <= year && (e.to === null || year < e.to);", "export const covers = (e, year) => e.from <= year && (e.to === null || e.to === \"present\" || year < e.to);"]]],
  ["a missing end is taken for a still-running era", "export const numeric = (e) => e != null && typeof e === \"object\" && isYear(e.from) && (e.to === null ||", "export const numeric = (e) => e != null && typeof e === \"object\" && isYear(e.from) && (e.to == null ||", "an-era-with-no-end-at-all-is-not-still-running",
    [["export const covers = (e, year) => e.from <= year && (e.to === null || year < e.to);", "export const covers = (e, year) => e.from <= year && (e.to == null || year < e.to);"]]],
  ["an uncertain date has a year", "const m = PLAIN.exec(s) || ISO.exec(s);", "const m = /(\\d{4})/.exec(s);", "year:c. 1860|1860"],
  ["a date and a year need not agree", "if (!m || Number(m[1]) !== year) return null;", "if (!m) return null;", "year:1860|1861"],
  ["a snapshot of another version is read", "snap.version !== VERSION", "false", "a-snapshot-of-the-first-version-is-refused"],
  ["an http base is accepted", "/^https:\\/\\/[^/?#\\s]+$/i", "/^https?:\\/\\/[^/?#\\s]+$/i", "href-needs-https"],
  ["a seeded region is not marked", "const seeded = e.seeded_from_archive === true;", "const seeded = false;", "accents-and-case-are-folded"],
  ["a refused era is reported as no era", "refused.length ? \"era-refused\" : \"no-era\"", "\"no-era\"", "a-refused-era-is-silent-and-counted-as-refused"],
  ["a place on the edge is not silent", "if (own(snap.places_silent, key) && VALID_SILENT.includes(snap.places_silent[key])) return no(snap.places_silent[key]);", "", "a-place-on-the-edge-is-silent"],
  ["any silence reason is believed", " && VALID_SILENT.includes(snap.places_silent[key])", "", "an-unknown-silence-reason-is-no-region"],
  ["an unchecked place is not flagged", "Array.isArray(snap.unchecked_edge) && snap.unchecked_edge.includes(d.key)", "false", "a-place-that-could-not-be-edge-checked-is-flagged"],
  ["a near-edge place is noted whatever its neighbours say", "if (kind === null || list.length === 0 || list.some((nb) => nb === region || !neighbourAgrees(snap, nb, year, e, boundary, pol))) return no(kind || \"edge\");", "", "a-place-near-an-edge-is-silent-where-its-neighbour-has-another-regime"],
  ["a near-edge place needs only ONE agreeing neighbour", "list.some((nb) => nb === region || !neighbourAgrees(", "list.every((nb) => nb === region || !neighbourAgrees(", "a-place-near-an-edge-is-silent-where-any-one-neighbour-differs"],
  ["a near-edge place with no neighbours is noted", "kind === null || list.length === 0 ||", "kind === null ||", "an-edge-place-with-no-neighbours-is-silent"],
  ["an unknown kind of edge is believed", "kind === null || list.length === 0", "list.length === 0", "an-edge-place-with-a-kind-the-library-does-not-know-is-silent"],
  ["a region is its own neighbour", "nb === region || !neighbourAgrees(", "!neighbourAgrees(", "an-edge-place-that-names-its-own-region-as-neighbour-is-silent"],
  ["a ring conflict is reported as an edge", "return no(kind || \"edge\");", "return no(\"edge\");", "a-place-in-a-neighbours-ring-is-silent-as-a-ring-conflict-where-they-differ"],
  ["the edge agreement is not recorded on the era", "edgeAgree: d.edgeAgree,", "edgeAgree: false,", "a-place-near-an-edge-keeps-its-note-where-its-neighbour-has-the-same-regime"],
  ["the assessed flag is not recorded on the era", "assessed: !d.unassessed,", "assessed: true,", "an-era-with-null-flags-is-allowed-when-the-snapshot-says-so"],
  ["a neighbour the snapshot does not hold is trusted", "if (typeof nb !== \"string\" || !own(snap.regions, nb) || !Array.isArray(snap.regions[nb])) return false;", "if (!own(snap.regions, nb)) return true;", "a-neighbour-the-snapshot-does-not-hold-is-unknown"],
  ["a neighbour with a refused era over the year is trusted", "if (dropped.some((d) => covers(d, year))) return false;", "", "a-neighbour-with-a-refused-era-over-the-year-is-silent"],
  ["a neighbour with no era for the year is trusted", "if (covering.length !== 1) return false;\n  const x = covering[0];", "if (covering.length > 1) return false;\n  const x = covering[0] || mine;", "a-place-near-an-edge-is-silent-where-its-neighbour-has-no-era-for-the-year"],
  ["a neighbour era that overlaps another elsewhere is trusted", "if (eras.some((o) => o !== x && numeric(o) && meets(x, o))) return false;\n  if (marginGate(", "if (marginGate(", "a-neighbour-era-that-overlaps-another-anywhere-is-silent"],
  ["a neighbour era marked approximate is trusted", "if (marginGate(x, year, pol) !== null) return false;", "if (flag(x.contested) === \"yes\" && marginGate(x, year, pol) !== null) return false;", "a-place-near-an-edge-is-silent-where-its-neighbour-era-is-approximate"],
  ["a neighbour era marked contested is trusted", "if (marginGate(x, year, pol) !== null) return false;", "if (flag(x.approx) === \"yes\" && marginGate(x, year, pol) !== null) return false;", "a-neighbour-marked-contested-is-silent"],
  ["a neighbour era's margins are ignored", "if (marginGate(x, year, pol) !== null) return false;", "if (flag(x.approx) === \"yes\" || flag(x.contested) === \"yes\") return false;", "margin-an-edge-place-keeps-its-note-where-the-neighbour-is-approx-but-well-inside-it"],
  ["a neighbour era within its margin is trusted", "if (marginGate(x, year, pol) !== null) return false;", "", "margin-an-edge-place-is-silent-where-the-neighbours-approx-era-is-within-its-margin"],
  ["a neighbour era contested about its regime is trusted", "if (marginGate(x, year, pol) !== null) return false;", "if (flag(x.approx) === \"yes\" && marginGate(x, year, pol) !== null) return false;", "margin-an-edge-place-is-silent-where-the-neighbours-era-is-contested-about-its-regime"],
  ["a neighbour the Atlas has not assessed is trusted whatever the policy says", "&& pol.unassessed !== \"allow\") return false;\n  if (label(x)", "&& false) return false;\n  if (label(x)", "a-neighbour-the-atlas-has-not-assessed-is-unknown-under-the-refuse-policy"],
  ["a neighbour the Atlas has not assessed is never allowed", "&& pol.unassessed !== \"allow\") return false;\n  if (label(x)", "&& true) return false;\n  if (label(x)", "a-neighbour-the-atlas-has-not-assessed-is-allowed-when-the-snapshot-says-so"],
  ["a neighbour's label need not be the same words", "if (label(x) !== label(mine)) return false;", "if (label(x).toLowerCase() !== label(mine).toLowerCase()) return false;", "a-neighbour-label-must-be-the-same-words"],
  ["any neighbour regime is agreement", "if (label(x) !== label(mine)) return false;", "", "a-place-near-an-edge-is-silent-where-its-neighbour-has-another-regime"],
  ["a neighbour's change in the year is not looked at", "if (!boundary && year === x.from) {", "if (false) {", "a-neighbour-whose-era-begins-this-year-after-another-regime-is-silent"],
  ["a neighbour's change is looked at even for a boundary note", "if (!boundary && year === x.from) {", "if (year === x.from) {", "a-boundary-note-needs-only-the-neighbours-newer-era"],
  ["a neighbour with no era before its first is trusted", "before.length === 0 || before.some(", "before.some(", "a-neighbour-whose-first-era-begins-this-year-is-unknown-before-it"],
  ["a neighbour's refused predecessor is ignored", "if (dropped.some((d) => d.to === year)) return false;", "", "a-neighbour-whose-predecessor-was-refused-is-unknown"],
  ["a neighbour's predecessor may have another label", "before.some((o) => label(o) !== label(mine) ||", "before.some((o) => false ||", "a-neighbour-whose-era-begins-this-year-after-another-regime-is-silent"],
  ["the assessed mark is not drawn", " data-era-assessed=\"${era.assessed === true ? \"1\" : \"0\"}\"", "", "render:note"],
  ["the edge mark is not drawn", "${era.edgeAgree === true ? ' data-era-edge-agree=\"1\"' : \"\"}", "", "render:edge-agree"],
  ["the approx mark is not drawn", "${era.approx === true ? ' data-era-approx=\"1\"' : \"\"}", "", "render:margin-marks"],
  ["the contested mark is not drawn", "${era.contested === true ? ' data-era-contested=\"1\"' : \"\"}", "", "render:margin-marks"],
  ["the note's words carry the era's bounds", "<span class=\"era-lab\">${esc(era.label)}</span>", "<span class=\"era-lab\">${esc(era.label)} (${era.from}-${era.to})</span>", "render:margin-words"],
  ["an unassessed note is drawn as assessed", "era.assessed === true ? \"1\" : \"0\"", "\"1\"", "render:unassessed"],
  ["the label is not escaped", "const esc = (s) => String(s).replace(/&/g, \"&amp;\").replace(/</g, \"&lt;\").replace(/>/g, \"&gt;\").replace(/\"/g, \"&quot;\");", "const esc = (s) => String(s);", "render:escapes"],
  ["the year is not carried", " data-era-year=\"${esc(era.year)}\"", "", "render:note"],
  ["the source is not a link", "era.href\n    ? `<a class=\"era-src\"", "false\n    ? `<a class=\"era-src\"", "render:note"],
  ["a boundary note is not marked", "${b ? ' data-era-boundary=\"1\"' : \"\"}", "", "render:boundary"],
  ["a boundary note says 'at the time'", "${b ? PRE_BOUNDARY : PRE_NORMAL}", "${PRE_NORMAL}", "render:boundary"],
  /* rule m: rulers */
  ["a region the contract says has no rulers is named a ruler", " || rs.has !== true", "", "ruler-a-region-the-contract-says-has-no-rulers-is-silent-though-reigns-are-listed"],
  ["overlapping reigns: the first is picked", "if (touching.length > 1) return no(\"overlap\");", "", "ruler-two-overlapping-reigns-are-silent-whichever-polity"],
  ["a reign's start margin does not widen it", "r.from_year - r.from_margin <= year", "r.from_year <= year", "ruler-the-year-before-the-federation-has-two-reigns-through-its-start-margin"],
  ["a reign's end margin does not widen it", "year <= r.to_year + (r.to_margin || 0)", "year <= r.to_year", "ruler-an-end-margin-of-1-widens-a-reign-one-year-past-its-end"],
  ["an open reign is measured from an end it has not got", "(r.to_year !== null && !(r.to_year - year > Math.max(n, r.to_margin)))", "(!(r.to_year - year > Math.max(n, r.to_margin)))", "ruler-an-open-reign-is-named-with-no-end-to-measure-from"],
  ["the floor is not applied at a reign's start", "year - r.from_year > Math.max(n, r.from_margin)", "year - r.from_year > r.from_margin", "ruler-within-5-years-of-the-reign-start-is-silent"],
  ["the floor is not applied at a reign's end", "r.to_year - year > Math.max(n, r.to_margin)", "r.to_year - year > r.to_margin", "ruler-within-5-years-of-the-reign-end-is-silent"],
  ["a year AT the reach of the start is allowed (at least, not more than)", "year - r.from_year > Math.max(n, r.from_margin)", "year - r.from_year >= Math.max(n, r.from_margin)", "ruler-the-year-AT-the-reach-is-silent-not-more-than-5"],
  ["a year AT the reach of the end is allowed", "r.to_year - year > Math.max(n, r.to_margin)", "r.to_year - year >= Math.max(n, r.to_margin)", "ruler-the-union-ruler-5-years-before-the-end-is-silent"],
  ["the snapshot's floor is ignored for rulers", "const n = floorOf(pol);\n  if (!(year - r.from_year", "const n = MARGIN_YEARS;\n  if (!(year - r.from_year", "ruler-with-the-floor-off-a-zero-margin-reign-is-named-up-to-the-year-before-its-end-1736"],
  ["a reign of another polity is named", "if (!Array.isArray(allowed) || !allowed.includes(r.polity_id)) return no(\"polity\");", "", "ruler-the-reign-of-another-polity-is-silent"],
  ["a regime the polity table does not list is allowed any polity", "if (!Array.isArray(allowed) || !allowed.includes(r.polity_id)) return no(\"polity\");", "if (Array.isArray(allowed) && !allowed.includes(r.polity_id)) return no(\"polity\");", "ruler-a-regime-the-polity-table-does-not-list-is-silent"],
  ["two eras over the year do not silence the ruler", "if (covering.length !== 1 || refused.length > 0) return no(\"no-era\");", "if (covering.length < 1 || refused.length > 0) return no(\"no-era\");", "ruler-two-kept-eras-over-the-year-is-silent"],
  ["a refused era over the year does not silence the ruler", "if (covering.length !== 1 || refused.length > 0) return no(\"no-era\");", "if (covering.length !== 1) return no(\"no-era\");", "ruler-a-refused-era-over-the-year-is-silent"],
  ["an unusable reign row is ignored", "if (!rs.reigns.every(reignOk)) return no(\"bad-rows\");", "", "ruler-a-region-with-an-unusable-reign-row-is-silent-whole"],
  ["the Atlas's name is changed", "return { name: r.name,", "return { name: r.name.toUpperCase(),", "ruler-a-year-well-inside-one-reign-names-it"],
  ["the polityId is not returned", "polityId: r.polity_id,", "polityId: null,", "ruler:fields"],
  ["a boundary-year note names a ruler", "ruler: d.boundary || d.edgeAgree ? null : rulerAt(snap, region, year),", "ruler: d.edgeAgree ? null : rulerAt(snap, region, year),", "note-a-boundary-year-note-names-no-ruler-though-a-reign-covers-it"],
  ["an edge note names a ruler", "ruler: d.boundary || d.edgeAgree ? null : rulerAt(snap, region, year),", "ruler: d.boundary ? null : rulerAt(snap, region, year),", "note-an-edge-note-names-no-ruler"],
  ["the note carries no ruler", "ruler: d.boundary || d.edgeAgree ? null : rulerAt(snap, region, year),", "ruler: null,", "note-a-ruler-well-inside-a-reign-is-on-the-note"],
  ["the ruler is drawn without being asked for", "opts && opts.rulers === true && era.ruler &&", "era.ruler &&", "render:ruler-off"],
  ["the ruler is never drawn", "? era.ruler : null;", "? null : null;", "render:ruler"],
  ["the ruler mark is not drawn", "${ru ? ` data-era-ruler=\"${esc(ru.name)}\"` : \"\"}", "", "render:ruler"],
  ["the ruler's words are not drawn", "${ru ? ` <span class=\"era-ruler\">(${esc(ru.name)})</span>` : \"\"}", "", "render:ruler"],
  ["the ruler's name is not escaped", "(${esc(ru.name)})</span>", "(${ru.name})</span>", "render:ruler-escapes"],
  ["the place is not drawn", " data-era-place=\"${esc(era.place)}\"", "", "render:note"],
  ["the place is not returned by eraAt", "region, place: d.key, id: e.id,", "region, place: null, id: e.id,", "render:note"],
];
for (const [label, from, to, must, extra] of faults) {
  if (!src.includes(from)) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; }
  let broken = src.replace(from, to);
  let cannot = false;
  for (const [a, b] of (extra || [])) { if (!broken.includes(a)) cannot = true; broken = broken.replace(a, b); }
  if (cannot) { n++; bad++; console.log("  FAIL  planted fault '" + label + "' could not be planted (the code changed)"); continue; }
  const d = fs.mkdtempSync(path.join(os.tmpdir(), "era-fault-")); const f = path.join(d, "era.mjs");
  fs.writeFileSync(f, broken);
  let failed;
  try { failed = failing(await import(pathToFileURL(f).href)); } catch (e) { failed = ["threw: " + e.message]; }
  n++; if (failed.includes(must)) console.log("  ok    planted fault '" + label + "' is caught (" + must + ")"); else { bad++; console.log("  FAIL  planted fault '" + label + "' was NOT caught (failed: " + failed.join(", ") + ")"); }
  fs.rmSync(d, { recursive: true, force: true });
}

// the component draws what the library describes: its template carries the attributes the gate relies on
const astro = fs.readFileSync(path.join(kit, "components", "EraNote.astro"), "utf8");
for (const needle of ['class="era-note"', "data-era={note.id}", "data-era-year={note.year}", 'data-era-boundary={note.boundary === true ? "1" : undefined}', 'data-era-assessed={note.assessed === true ? "1" : "0"}', 'data-era-approx={note.approx === true ? "1" : undefined}', 'data-era-contested={note.contested === true ? "1" : undefined}', 'data-era-margin-unsourced={note.unsourced === true ? "1" : undefined}', 'data-era-edge-agree={note.edgeAgree === true ? "1" : undefined}', "PRE_BOUNDARY : PRE_NORMAL", 'class="era-pre"', 'class="era-lab"', 'class="era-src"', 'rel="noopener"', "note.href", "era && era.id && era.label ? era : null",
  "note ? claim(Astro.request, ERA_CSS_KEY) : false", "<style is:inline data-era-css set:html={ERA_CSS} />"]) {
  ok("EraNote.astro carries " + needle, astro.includes(needle));
}
const astroCode = astro.replace(/\/\*[\s\S]*?\*\//g, "");
ok("EraNote.astro imports nothing of an archive's", !/from\s+["'](?!\.\.\/lib\/(era|rec)\.js)/.test(astroCode));
ok("EraNote.astro has no component <style> of its own (a bundled style lands on every page that imports the component)", !/<style(?![^>]*is:inline)/.test(astroCode) && !/is:global/.test(astroCode));
ok("the one style is drawn only for a note that exists, once per page render (claim on the request, as Rec.astro does)", astroCode.split("<style").length === 2 && /const drawCss = note \? claim\(/.test(astroCode));
const claimOk = (() => { const sc = {}, sc2 = {}; return E.ERA_CSS_KEY && R.claim(sc, E.ERA_CSS_KEY) === true && R.claim(sc, E.ERA_CSS_KEY) === false && R.claim(sc2, E.ERA_CSS_KEY) === true; })();
ok("the claim lets the first note of a page draw the style and no second one; another page (request) starts clean", claimOk);
ok("the style is the muted, token-driven look it was (the same rules, nothing added)", /^\.era-note\{display:block;/.test(E.ERA_CSS) && E.ERA_CSS.includes("var(--ink-2,#444)") && E.ERA_CSS.includes("var(--sans,system-ui,sans-serif)") && !/(?:url\(|@import|!important|position:|background)/.test(E.ERA_CSS) && E.ERA_CSS.length < 800, String(E.ERA_CSS.length));
ok("EraNote.astro draws no image", !/<img|<svg|background-image|flag/i.test(astroCode));

// the gate reads what the library draws, and fails when the page is changed
const t = fs.mkdtempSync(path.join(os.tmpdir(), "era-gate-"));
const snapPath = path.join(t, "era-snapshot.json");
fs.writeFileSync(snapPath, JSON.stringify(FIX.gate_snapshot));
const CSS = `<style is:inline data-era-css>${E.ERA_CSS}</style>`;
/* a page as the component draws it: the style once, ahead of the first note, and none where there is no note */
const page = (body, head = "") => `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>A page</title>${head}</head><body><main><h1>A person</h1><div class="rec"><div class="v">Hentzau${body ? CSS + body : ""}</div></div></main></body></html>`;
const note = (p, y) => E.renderEra(E.eraAt(FIX.gate_snapshot, p, y));
const gate = (html, extra = []) => {
  const dist = path.join(t, "dist"); fs.rmSync(dist, { recursive: true, force: true });
  fs.mkdirSync(path.join(dist, "people", "a"), { recursive: true });
  fs.writeFileSync(path.join(dist, "people", "a", "index.html"), html);
  const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => k !== "ARCHIVE_OUT"));
  const r = spawnSync("python3", [path.join(here, "checkera.py"), "--dist", dist, "--snapshot", snapPath, ...extra], { encoding: "utf8", env });
  return { code: r.status, out: (r.stdout || "") + (r.stderr || "") };
};
const good = gate(page(note("Hentzau", 1750)));
ok("gate: a note the library drew is accepted (exit 0)", good.code === 0, good.out);
ok("gate: the page's own markup is what it reads (1 note, 1 page)", /1 page\(s\) read, 1 with a note, 1 note\(s\)/.test(good.out), good.out);
const wrongYear = gate(page(note("Hentzau", 1750).replace('data-era-year="1750"', 'data-era-year="1800"')));
ok("gate: the same note with the year an era ENDS in (outside from <= year < to) fails (year)", wrongYear.code === 1 && /year 1/.test(wrongYear.out), wrongYear.out);
const wrongWords = gate(page(note("Hentzau", 1750).replace("Kingdom of Ruritania", "Empire of Ruritania")));
ok("gate: the same note with other words fails (label)", wrongWords.code === 1 && /label 1/.test(wrongWords.out), wrongWords.out);
const living = gate(page(note("Hentzau", 1750), '<meta name="robots" content="noindex,nofollow">'));
ok("gate: a note on a noindex page fails", living.code === 1 && /noindex 1/.test(living.out), living.out);
const bnd = gate(page(note("Hentzau", 1850)));
ok("gate: a boundary-year note the library drew is accepted, and counted", bnd.code === 0 && /1 on a boundary year/.test(bnd.out), bnd.out);
const bndUnmarked = gate(page(note("Hentzau", 1850).replace(' data-era-boundary="1"', "")));
ok("gate: the same note without its boundary mark fails (boundary)", bndUnmarked.code === 1 && /boundary 1/.test(bndUnmarked.out), bndUnmarked.out);
const bndWords = gate(page(note("Hentzau", 1850).replace("From that year", "At the time")));
ok("gate: the same note worded 'at the time' fails (boundary)", bndWords.code === 1 && /boundary 1/.test(bndWords.out), bndWords.out);
const recent = gate(page(E.renderEra(E.eraAt(FIX.gate_snapshot, "Zenda", 1975)).replace('data-era-year="1975"', 'data-era-year="1995"')));
ok("gate: a note in the running era at or after the quiet-rule year fails (recent)", recent.code === 1 && /recent 1/.test(recent.out), recent.out);
const oldId = gate(page(note("Hentzau", 1750).replace("ruritania--era-1700", "ruritania--1700")));
ok("gate: an id that is not the contract's (region--year) fails (unknown)", oldId.code === 1 && /unknown 1/.test(oldId.out), oldId.out);
const eraLink = gate(page(note("Hentzau", 1750).replace("#era-1700", "")));
ok("gate: a link to the region, not the era, fails (source)", eraLink.code === 1 && /source 1/.test(eraLink.out), eraLink.out);
const none = gate(page(""));
ok("gate: a site with no note at all is not a pass (exit 2)", none.code === 2, none.out);
// the era style belongs to a page with a note, once
const twoNotes = page(note("Hentzau", 1750) + " " + note("Hentzau", 1860));
ok("gate: a page with several notes and ONE era style is accepted, and the page is counted as carrying it", gate(twoNotes).code === 0 && /1 page\(s\) carry the era style, one each/.test(gate(twoNotes).out), gate(twoNotes).out);
const noCss = gate(page(note("Hentzau", 1750)).replace(CSS, ""));
ok("gate: a page with a note and NO era style fails (css)", noCss.code === 1 && /css 1/.test(noCss.out), noCss.out);
const twiceCss = gate(page(note("Hentzau", 1750) + CSS + note("Hentzau", 1860)));
ok("gate: a page that draws the era style twice fails (css)", twiceCss.code === 1 && /css 1/.test(twiceCss.out), twiceCss.out);
const strayCss = gate(page("") .replace("</main>", CSS + "</main>"), []);
ok("gate: a page with the era style and no note fails (css): it is the weight the old bundled style put on every page", strayCss.code === 2 || /css 1/.test(strayCss.out) || strayCss.code === 1, strayCss.out);
{
  const dist = path.join(t, "dist2"); fs.rmSync(dist, { recursive: true, force: true });
  fs.mkdirSync(path.join(dist, "a"), { recursive: true }); fs.mkdirSync(path.join(dist, "b"), { recursive: true });
  fs.writeFileSync(path.join(dist, "a", "index.html"), page(note("Hentzau", 1750)));
  fs.writeFileSync(path.join(dist, "b", "index.html"), page("").replace("</main>", CSS + "</main>"));
  const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => k !== "ARCHIVE_OUT"));
  const r = spawnSync("python3", [path.join(here, "checkera.py"), "--dist", dist, "--snapshot", snapPath], { encoding: "utf8", env });
  ok("gate: one page with a note and one with a stray era style: the stray one fails (css 1)", r.status === 1 && /css 1/.test(r.stdout), r.stdout);
  fs.writeFileSync(path.join(dist, "b", "index.html"), page(""));
  const r2 = spawnSync("python3", [path.join(here, "checkera.py"), "--dist", dist, "--snapshot", snapPath], { encoding: "utf8", env });
  ok("gate: a page with no note carries no era style, and that passes", r2.status === 0, r2.stdout);
  const nm = fs.readFileSync(path.join(dist, "b", "index.html"), "utf8");
  ok("the page without a note has no era CSS marker at all", !nm.includes("data-era-css") && !nm.includes(".era-note"));
}
const assessedWrong = gate(page(note("Hentzau", 1750).replace('data-era-assessed="1"', 'data-era-assessed="0"')));
ok("gate: a note that says it rests on an unassessed era when the snapshot says assessed fails (assessed)", assessedWrong.code === 1 && /assessed 1/.test(assessedWrong.out), assessedWrong.out);
const assessedMissing = gate(page(note("Hentzau", 1750).replace(' data-era-assessed="1"', "")));
ok("gate: a note with no assessed mark fails (assessed)", assessedMissing.code === 1 && /assessed 1/.test(assessedMissing.out), assessedMissing.out);
const edgeNoPlace = gate(page(note("Hentzau", 1750).replace('data-era-assessed="1"', 'data-era-assessed="1" data-era-edge-agree="1"')));
ok("gate: an edge-agree mark where the snapshot holds no place that could carry it fails (edge)", edgeNoPlace.code === 1 && /edge 1/.test(edgeNoPlace.out), edgeNoPlace.out);

/* THE RE-DERIVATION (rule m and the gate gap): the gate recomputes every mark of a built note from the snapshot, its place and its year, and fails a mark that is
   missing, extra or wrong, a ruler the snapshot does not name, and text that is not the snapshot's words. The real renderer draws the notes; the real gate reads them. */
const RS = FIX.other_snapshots.rulers;
const rsPath = path.join(t, "era-snapshot-rulers.json");
fs.writeFileSync(rsPath, JSON.stringify(RS));
const rgate = (html, extra = []) => {
  const dist = path.join(t, "dist-r"); fs.rmSync(dist, { recursive: true, force: true });
  fs.mkdirSync(path.join(dist, "people", "a"), { recursive: true });
  fs.writeFileSync(path.join(dist, "people", "a", "index.html"), html);
  const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => k !== "ARCHIVE_OUT"));
  const r = spawnSync("python3", [path.join(here, "checkera.py"), "--dist", dist, "--snapshot", rsPath, ...extra], { encoding: "utf8", env });
  return { code: r.status, out: (r.stdout || "") + (r.stderr || "") };
};
const rnote = (p, y, rulers = false) => E.renderEra(E.eraAt(RS, p, y), { rulers });
const MARKS = [
  // [mark, a place and year whose note carries it, the attribute as drawn, the gate's category]
  ["data-era-boundary", "Tidy Town", 1800, ' data-era-boundary="1"', "boundary"],
  ["data-era-assessed", "Rulertown", 1745, ' data-era-assessed="1"', "assessed"],
  ["data-era-approx", "Rulertown", 1830, ' data-era-approx="1"', "approx"],
  ["data-era-contested", "Dispute Town", 1750, ' data-era-contested="1"', "approx"],
  ["data-era-margin-unsourced", "Soft Town", 1750, ' data-era-margin-unsourced="1"', "approx"],
  ["data-era-edge-agree", "Rulerborder Town", 1750, ' data-era-edge-agree="1"', "edge"],
  ["data-era-place", "Rulertown", 1745, ' data-era-place="rulertown"', "place"],
];
for (const [mark, place, year, attr, cat] of MARKS) {
  const base = rnote(place, year);
  ok("gate (re-derivation): the note the library drew with " + mark + " passes", base.includes(attr) && rgate(page(base)).code === 0, rgate(page(base)).out);
  const gone = rgate(page(base.replace(attr, "")));
  ok("gate (re-derivation): the same note with " + mark + " REMOVED fails (" + cat + ")", gone.code === 1 && new RegExp(cat + " 1").test(gone.out), gone.out);
}
for (const [mark, place, year, attr, cat] of MARKS.filter((m) => !["data-era-assessed", "data-era-place"].includes(m[0]))) {
  // the mark ADDED to a note whose place and year do not carry it
  const plain = rnote("Rulertown", 1745);
  const added = rgate(page(plain.replace(' data-era-place="rulertown"', attr + ' data-era-place="rulertown"')));
  ok("gate (re-derivation): a note with " + mark + " ADDED where the snapshot does not give it fails (" + cat + ")", added.code === 1 && new RegExp(cat + " 1").test(added.out), added.out);
}
{
  const wrongVal = rgate(page(rnote("Rulertown", 1745).replace('data-era-assessed="1"', 'data-era-assessed="0"')));
  ok("gate (re-derivation): data-era-assessed with the wrong value fails (assessed)", wrongVal.code === 1 && /assessed 1/.test(wrongVal.out), wrongVal.out);
  const wrongPlace = rgate(page(rnote("Rulertown", 1745).replace('data-era-place="rulertown"', 'data-era-place="plain town"')));
  ok("gate (re-derivation): a note drawn for another place (same year, another region) fails (place)", wrongPlace.code === 1 && /place 1/.test(wrongPlace.out), wrongPlace.out);
  const unknownPlace = rgate(page(rnote("Rulertown", 1745).replace('data-era-place="rulertown"', 'data-era-place="nowhere"')));
  ok("gate (re-derivation): a place the snapshot does not map fails (place)", unknownPlace.code === 1 && /place 1/.test(unknownPlace.out), unknownPlace.out);
  const unfolded = rgate(page(rnote("Rulertown", 1745).replace('data-era-place="rulertown"', 'data-era-place="Rulertown"')));
  ok("gate (re-derivation): a place that is not the folded key fails (place)", unfolded.code === 1 && /place 1/.test(unfolded.out), unfolded.out);
  const silentNote = rgate(page(rnote("Rulertown", 1745).replace('data-era-year="1745"', 'data-era-year="1736"')));
  ok("gate (re-derivation): the same place and a year the library is silent in still passes (1736 is a year the library draws a note for: control)", silentNote.code === 0, silentNote.out);
  const lib0 = rgate(page(rnote("Rulertown", 1745).replace('data-era-year="1745"', 'data-era-year="1860"')));
  ok("gate (re-derivation): a note for a place and year the library would not draw at all fails (silent)", lib0.code === 1 && /silent 1/.test(lib0.out), lib0.out);
  const extraText = rgate(page(rnote("Rulertown", 1745).replace("</a></span>", "</a> (and more)</span>")));
  ok("gate (re-derivation): text added inside the note fails (text)", extraText.code === 1 && /text 1/.test(extraText.out), extraText.out);
  const labelText = rgate(page(rnote("Rulertown", 1745).replace("Kingdom of Ruritania", "Kingdom of Ruritania, Greater")));
  ok("gate (re-derivation): the label changed in the note's text fails (label, text)", labelText.code === 1 && /label 1/.test(labelText.out) && /text 1/.test(labelText.out), labelText.out);
}
// rulers
{
  const withR = rnote("Rulertown", 1745, true);
  const g1 = rgate(page(withR), ["--rulers"]);
  ok("gate (rulers): a note that names the Atlas's ruler passes, and is counted", g1.code === 0 && /1 note\(s\) name a ruler/.test(g1.out) && /rulers are opted in/.test(g1.out), g1.out);
  ok("gate (rulers): ...also without --rulers (a ruler that is there is verified either way)", rgate(page(withR)).code === 0 && /rulers are not opted in/.test(rgate(page(withR)).out));
  const bare = rnote("Rulertown", 1745);
  ok("gate (rulers): a note with no ruler passes without --rulers (the archive has not opted in)", rgate(page(bare)).code === 0);
  const miss = rgate(page(bare), ["--rulers"]);
  ok("gate (rulers): ... and fails with --rulers, when the snapshot names a ruler the note leaves out (ruler)", miss.code === 1 && /ruler 1/.test(miss.out), miss.out);
  const silentOk = rgate(page(rnote("Rulertown", 1736, true)), ["--rulers"]);
  ok("gate (rulers): a note whose year is within a reign's margin carries no ruler, and passes with --rulers", silentOk.code === 0 && /0 note\(s\) name a ruler/.test(silentOk.out), silentOk.out);
  const stripped = withR.replace(' data-era-ruler="Rudolf II"', "").replace(' <span class="era-ruler">(Rudolf II)</span>', "");
  ok("gate (rulers): the ruler stripped by hand is the bare note: passes without --rulers, fails with it", stripped === bare && rgate(page(stripped), ["--rulers"]).code === 1);
  const inject = (html, name) => html.replace(' data-era-place="', ' data-era-place="').replace(/(data-era-place="[^"]*")/, '$1 data-era-ruler="' + name + '"').replace('</span> <a class="era-src"', '</span> <span class="era-ruler">(' + name + ')</span> <a class="era-src"');
  const bad = (label, html) => { const g = rgate(page(html), ["--rulers"]); ok("gate (rulers): " + label + " fails (ruler)", g.code === 1 && /ruler 1/.test(g.out), g.out); };
  bad("a ruler other than the one the snapshot names for the year", inject(bare, "Rudolf I"));
  bad("a ruler whose name is the Atlas's, normalised (\"Rudolf 2\")", inject(bare, "Rudolf 2"));
  bad("a ruler on a year inside a reign's margin of its end (1736)", inject(rnote("Rulertown", 1736), "Rudolf I"));
  bad("a ruler on an overlap year (1830: two reigns)", inject(rnote("Rulertown", 1830), "Francis"));
  bad("a ruler of another polity than the era's regime allows (1770)", inject(rnote("Rulertown", 1770), "Karl the Elder"));
  bad("a ruler on a boundary-year note", inject(rnote("Tidy Town", 1800), "Tidy Karl"));
  bad("a ruler on an edge note", inject(rnote("Rulerborder Town", 1750), "Rudolf II"));
  bad("a ruler on a note of a region that has no rulers", inject(rnote("Plain Town", 1750), "Plain King"));
  bad("a ruler on a note of a region with no rulers entry at all", inject(rnote("Nofield Town", 1750), "Nobody"));
  bad("a ruler span without its data-era-ruler mark", withR.replace(' data-era-ruler="Rudolf II"', ""));
  bad("a data-era-ruler mark without its words", withR.replace(' <span class="era-ruler">(Rudolf II)</span>', ""));
  bad("a ruler mark whose words differ", withR.replace("(Rudolf II)", "(Rudolf the Second)"));
  bad("a ruler mark that is empty", withR.replace('data-era-ruler="Rudolf II"', 'data-era-ruler=""'));
  const reign1830 = rgate(page(rnote("Rulertown", 1836, true)), ["--rulers"]);
  ok("gate (rulers): the Atlas's name with an ampersand and an accent, escaped by the renderer, passes", rgate(page(rnote("Rulertown", 1888, true)), ["--rulers"]).code === 0 && reign1830.code === 0, reign1830.out);
}
fs.rmSync(t, { recursive: true, force: true });

console.log(bad ? "\n" + bad + " of " + n + " FAILED" : "\n  ok    " + n + " checks: the era note, its markup, and the gate that reads it");
process.exit(bad ? 1 : 0);
