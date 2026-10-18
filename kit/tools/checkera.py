#!/usr/bin/env python3
"""The gate behind the "at the time" notes: does every note a BUILT site prints say only what the snapshot supports?

kit/components/EraNote.astro draws `<span class="era-note" data-era="<region>--era-<from>" data-era-year="<year>">` (the id is the
Record Atlas contract's own era id) and, for a year that is a boundary, `data-era-boundary="1"`. This reads the built HTML (not the
template: a template that is right can still be fed a wrong year) and the era snapshot the archive commits, and fails on:

  snapshot   the snapshot itself is malformed: wrong version, no contract version/stamp/hash, a place sent to a region it does not
             hold, an era without whole-number years (or an open end not marked present), an era whose id or url is not the one
             its region and start imply, an era without a label, a policy it does not understand
  untracked  (--require-tracked) the snapshot is not committed: a build from a checkout would not have it
  noindex    a note on a page that says noindex (a living, held-out or withheld person's page: rule c)
  living     a note on a page marked data-living, or listed in --living-urls (the archive's own living list)
  unknown    a note whose data-era is not an era id the snapshot holds (the contract's id: <region>--era-<from>)
  ineligible a note on an era that the snapshot's policy refuses (approximate under approx = refuse; contested under contested =
             refuse, or without contestedScope "bounds" under contested = scope, or of scope regime or part), that overlaps another
             era of its region, whose label is empty, or (unless the snapshot's policy says unassessed = allow) that the Atlas has not
             assessed (null)
  margin     a note whose year is not MORE THAN max(N, margin) from each of the era's bounds (rule l: year - from > max(N, from_margin)
             and to - year > max(N, to_margin), the end only for a closed era; N = the policy's margin_years, and N more where
             margin_sourced is false), or on an era whose recorded margin_ok disagrees with its margins
  approx     a note that is, or is not, marked data-era-approx="1" / data-era-contested="1" / data-era-margin-unsourced="1" where the
             snapshot's era is, or is not, flagged approximate / contested / carries a margin the Atlas did not source
  year       a note whose data-era-year is missing, not a whole number, or outside the era: from <= year < to (to null: no end)
  recent     a note on the still-running era for a year at or after the snapshot's recent_from (the quiet rule)
  boundary   a note that is, or is not, marked data-era-boundary="1" and worded "From that year" when its year is, or is not, the
             first year of an era that follows another (and a boundary year when the snapshot's policy is not "newer")
  label      a note whose words differ from the snapshot's label for the era, or that has no label, or two
  assessed   a note whose data-era-assessed is missing or is not "1" exactly where the snapshot says the era is assessed (neither
             contested nor approx null) and "0" where it is not
  edge       a note marked data-era-edge-agree where the snapshot has no place that could carry it: the policy is strict, or no place
             of the era's region has edge neighbours (the mark says "I stand at an edge and my neighbours agree")
  css        the era style (<style data-era-css>, drawn once by the first note of a page) is missing from a page that has a note,
             drawn twice, or drawn on a page that has no note (the weight the component's old bundled style put on every page)
  place      a note with no data-era-place, a place the snapshot does not map, or a place that maps to another era than the one the note names
  silent     a note the library would not have drawn at all for its place and year (the gate re-derives every note: era, marks, words, link, ruler)
  text       a note whose whole text is not exactly what the snapshot gives for its era (the mark, the label, the ruler if any, the source): nothing may be added
  ruler      a ruler (data-era-ruler, span.era-ruler) the snapshot does not name for the place and year (the reign does not cover the year, overlaps another,
             lies within the margin of its bounds, is of a polity the era's regime does not allow, or the region has no rulers), whose name is not the
             Atlas's exactly, or on a boundary or edge note; with --rulers also a MISSING ruler where the snapshot names one
  source     a note that does not say where it came from ("per the Record Atlas", or "per the Record Atlas, drawn from this archive's own
             research" for an era the snapshot marks seeded_from_archive: rule f, never the plain phrase there; --seeded-text gives the
             archive's own words), or whose link is not the era's own url on the Atlas (rule e)
  seeded     a note on a seeded era (the Atlas's bands came from this estate's own research) that lacks data-era-seeded="1", or a note
             on an era that is not seeded that carries it (the mark is re-derived from the snapshot: missing, extra or wrong all fail)

It prints COUNTS ONLY: never a place, a person, a date or a path. ZERO PAGES EXAMINED IS NOT A PASS, and neither are zero notes
(--min-notes, default 1): a gate that found nothing because it looked in the wrong place has not found that nothing is wrong. It
reads the tree twice and throws its results away if the tree changed while it ran (another build in flight). ARCHIVE_OUT beats
--dist, as everywhere in this kit (outdir.py). With --strict-unassessed it also fails a snapshot whose policy allows eras the Atlas has
not assessed (every region era was null on contested/approx in contract 1.7.0).

THE RE-DERIVATION. A note carries data-era-place (the folded place it was drawn for), so the gate calls the library's own era_at(snapshot, place,
year) for it and holds the note to the result: the era, the year, every mark (boundary, assessed, approx, contested, margin-unsourced, edge-agree)
MISSING, EXTRA or WRONG, the words, the link and the ruler. A mark taken off a built note fails as surely as one added. --rulers says the archive has
opted in to rulers (EraNote rulers): then a note whose snapshot names a ruler must carry it; without it a ruler that is there is still verified.

    python3 checkera.py --dist dist --snapshot src/data/era-snapshot.json [--living-urls living.json] [--require-tracked] [--rulers]
Exit: 0 clean; 1 any failure; 2 could not see what it needed (no pages, no snapshot, too few notes, tree changed).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eralib  # noqa: E402
import outdir  # noqa: E402

ID = re.compile(r"^([a-z0-9][a-z0-9-]*)--era-(\d{1,4})$")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.robots = ""
        self.living = False
        self.notes = []
        self.css = []            # the text of each <style data-era-css>
        self.in_css = False
        self.stack = []          # (tag, note-or-None, part-or-None)
        self.cur = None          # the note being read

    def _attrs(self, attrs):
        return {k: (v if v is not None else "") for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        a = self._attrs(attrs)
        if tag == "meta" and a.get("name", "").lower() == "robots":
            self.robots += " " + a.get("content", "").lower()
        if a.get("data-living", "").lower() in ("1", "true", "yes"):
            self.living = True
        cls = a.get("class", "").split()
        if tag == "style" and "data-era-css" in a:
            self.in_css = True
            self.css.append("")
        note = None
        part = None
        if "data-era" in a:
            note = {"id": a["data-era"], "year": a.get("data-era-year"), "boundary": a.get("data-era-boundary"),
                    "assessed": a.get("data-era-assessed"), "approx": a.get("data-era-approx"), "contested": a.get("data-era-contested"), "unsourced": a.get("data-era-margin-unsourced"), "edge_agree": a.get("data-era-edge-agree"), "seeded": a.get("data-era-seeded"), "place": a.get("data-era-place"),
                    "ruler": a.get("data-era-ruler"), "text": "", "pres": [], "labs": [], "rus": [],
                    "srcs": [], "hrefs": []}
            self.notes.append(note)
            self.cur = note
        elif self.cur is not None:
            if "era-pre" in cls:
                part = "pre"
                self.cur["pres"].append("")
            if "era-lab" in cls:
                part = "lab"
                self.cur["labs"].append("")
            if "era-ruler" in cls:
                part = "ru"
                self.cur["rus"].append("")
            if "era-src" in cls:
                part = "src"
                self.cur["srcs"].append("")
                self.cur["hrefs"].append(a.get("href"))
        if tag not in VOID:
            self.stack.append((tag, note, part))

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_css = False
        while self.stack:
            t, note, part = self.stack.pop()
            if note is not None and self.cur is note:
                self.cur = None
            if t == tag:
                break

    def handle_data(self, data):
        if self.in_css:
            self.css[-1] += data
            return
        if self.cur is None:
            return
        self.cur["text"] += data
        for t, note, part in reversed(self.stack):
            if part == "pre":
                self.cur["pres"][-1] += data
                break
            if part == "lab":
                self.cur["labs"][-1] += data
                break
            if part == "ru":
                self.cur["rus"][-1] += data
                break
            if part == "src":
                self.cur["srcs"][-1] += data
                break
            if note is not None:
                break


def norm(s):
    return " ".join((s or "").split())


def check_snapshot(snap):
    """The snapshot's own shape. Returns a list of reasons (counted, never printed with a name)."""
    bad = []
    if not isinstance(snap, dict) or snap.get("version") != eralib.VERSION:
        return ["version"]
    c = snap.get("contract")
    if not (isinstance(c, dict) and c.get("name") == "recordatlas-context" and isinstance(c.get("version"), str)
            and re.fullmatch(r"\d+\.\d+\.\d+", c["version"]) and isinstance(c.get("generated"), str)
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", c["generated"]) and isinstance(c.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", c["sha256"])):
        bad.append("no contract version, stamp and hash")
    if eralib.region_href(snap, "x") is None:
        bad.append("no usable atlas base")
    at = snap.get("atlas") if isinstance(snap.get("atlas"), dict) else {}
    src = at.get("rings_source")
    sha = at.get("rings_sha256")
    if not (src in ("contract", "file", "none") and ((src == "file" and isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha))
                                                      or (src != "file" and sha is None))):
        bad.append("the source of the rings is not recorded (atlas.rings_source and rings_sha256)")
    pol = snap.get("policy")
    if not (isinstance(pol, dict) and pol.get("unassessed") in ("refuse", "allow") and pol.get("boundary") in ("newer", "silent")
            and eralib.is_year(pol.get("recent_from")) and isinstance(pol.get("edge_km"), (int, float))
            and pol.get("edge") in ("agree", "strict")):
        bad.append("policy missing or not understood")
    elif not (pol.get("approx") in ("refuse", "margin") and pol.get("contested") in ("refuse", "scope", "margin")
              and eralib.is_margin(pol.get("margin_years")) and isinstance(pol.get("margins"), dict)):
        bad.append("policy has no approx / contested / margin_years / margins (rule l)")
        pol = {}
    rp = pol.get("ruler_polities") if isinstance(pol, dict) else None
    if pol and not (isinstance(rp, dict) and all(isinstance(k, str) and isinstance(v, list) and v and all(isinstance(x, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", x) for x in v)
                                                  for k, v in rp.items())):
        bad.append("policy has no ruler_polities (rule m)")
    if not isinstance(snap.get("regions"), dict) or not isinstance(snap.get("places"), dict):
        return bad + ["regions or places missing"]
    rl = snap.get("rulers")
    if not isinstance(rl, dict):
        bad.append("rulers missing (rule m)")
        rl = {}
    for rid, rs in rl.items():
        if rid not in snap["regions"]:
            bad.append("rulers for a region the snapshot does not hold")
        elif not (isinstance(rs, dict) and rs.get("has") in (True, False, None) and isinstance(rs.get("reigns"), list)
                  and (rs.get("why") is None or isinstance(rs.get("why"), str))):
            bad.append("a region's rulers are not {has, why, reigns}")
        elif rs["has"] is True and not (rs["reigns"] and rs.get("why") is None and all(eralib.reign_ok(r) for r in rs["reigns"])):
            bad.append("a region marked as having rulers whose reigns are missing or unusable")
        elif rs["has"] is not True and (rs["reigns"] or not rs.get("why")):
            bad.append("a region without rulers that carries reigns, or does not say why")
    silent = snap.get("places_silent")
    if not isinstance(silent, dict) or any(v not in eralib.VALID_SILENT for v in silent.values()):
        bad.append("places_silent missing or has a reason it does not know")
        silent = {}
    unchecked = snap.get("unchecked_edge")
    if not isinstance(unchecked, list):
        bad.append("unchecked_edge missing")
        unchecked = []
    for k, r in snap["places"].items():
        if k != eralib.fold(k) or not k:
            bad.append("a place key is not folded")
        if r not in snap["regions"]:
            bad.append("a place goes to a region the snapshot lacks")
        if k in silent:
            bad.append("a place is both mapped and silent")
    for k in unchecked:
        if k not in snap["places"]:
            bad.append("an unchecked place is not a mapped place")
    en = snap.get("edge_neighbours")
    if not isinstance(en, dict):
        bad.append("edge_neighbours missing")
        en = {}
    elif isinstance(pol, dict) and pol.get("edge") == "strict" and en:
        bad.append("edge neighbours under a strict edge policy")
    for k, v in en.items():
        if k not in snap["places"]:
            bad.append("an edge place is not a mapped place")
        elif not (isinstance(v, dict) and v.get("kind") in eralib.EDGE_KINDS and isinstance(v.get("regions"), list) and v["regions"]
                  and all(isinstance(r, str) and r in snap["regions"] and r != snap["places"][k] for r in v["regions"])):
            bad.append("an edge place whose neighbours are missing, unknown or its own region")
        elif k in unchecked:
            bad.append("an edge place that is also unchecked")
        elif src == "none":
            bad.append("an edge place although no rings were used")
    q = snap.get("quality")
    if not (isinstance(q, dict) and isinstance(q.get("counts"), dict) and isinstance(q.get("gaps"), list) and isinstance(q.get("overlaps"), list)):
        bad.append("the contract's quality block is missing")
    pol = pol if isinstance(pol, dict) else {}
    for rid, eras in snap["regions"].items():
        if not isinstance(eras, list):
            bad.append("a region's eras are not a list")
            continue
        for e in eras:
            if not eralib.numeric(e):
                bad.append("an era without whole-number years")
                continue
            if e["to"] is None and e.get("present") is not True:
                bad.append("an open end on an era not marked present")
            if e.get("id") != eralib.era_id(rid, e["from"]) or eralib.era_href(snap, rid, e) is None:
                bad.append("an era whose id or url is not the one its region and start imply")
            if not isinstance(e.get("label"), str) or not e["label"].strip():
                bad.append("an era without a label")
            if not isinstance(e.get("basis"), str) or e.get("seeded_from_archive") is not e["basis"].startswith("seeded:"):
                bad.append("an era whose seeded flag does not follow its basis")
            if e.get("assessed") is not (e.get("approx") is not None and e.get("contested") is not None) or not (
                    e.get("why") is None or (isinstance(e["why"], str) and e["why"].strip())):
                bad.append("an era whose assessed flag does not follow its contested and approx, or whose why is not text or null")
            if not all(e.get(k) is None or eralib.is_margin(e.get(k)) for k in ("from_margin", "to_margin")) \
                    or e.get("margin_src") not in (None, "contract", "archive", "fallback") \
                    or e.get("margin_sourced") not in (None, True, False) \
                    or e.get("contested_scope") not in (None,) + eralib.SCOPES:
                bad.append("an era with a margin, margin source or contested scope that is not understood")
            elif eralib.margin_span(e, eralib.floor_of(pol)) is not None:
                # the recorded decision follows the margins, the margins exist where the era is flagged, and the policy allows the flag
                needs_to = not eralib.is_open(e)
                if (eralib.flag(e.get("approx")) == "yes" or eralib.flag(e.get("contested")) == "yes") and not (
                        eralib.is_margin(e.get("from_margin")) and (not needs_to or eralib.is_margin(e.get("to_margin")))):
                    bad.append("a flagged era with no margin")
                sp = eralib.margin_span(e, eralib.floor_of(pol))
                if e.get("margin_ok") != sp:
                    bad.append("an era whose margin_ok does not follow its margins")
            elif e.get("margin_ok") is not None:
                bad.append("a clean era with a margin_ok")
            if e.get("contested_scope") in ("regime", "part"):
                bad.append("an era kept although its contested scope is regime or part")
            if eralib.flag(e.get("approx")) == "yes" and pol.get("approx") != "margin":
                bad.append("an approximate era kept although the policy refuses it")
            if eralib.flag(e.get("contested")) == "yes" and (pol.get("contested") not in ("scope", "margin") or e.get("contested_scope") in ("regime", "part")
                                                         or (e.get("contested_scope") is None and pol.get("contested") != "margin")):
                bad.append("a contested era kept although the policy or its scope refuses it")
    return bad


def scan(dist):
    pages = []
    for d, ds, fs in os.walk(dist):
        ds[:] = sorted(ds)
        for f in sorted(fs):
            if f.endswith(".html"):
                pages.append(os.path.join(d, f))
    return pages


def url_of(dist, p):
    rel = os.path.relpath(p, dist).replace(os.sep, "/")
    rel = rel[:-len("index.html")] if rel.endswith("index.html") else rel
    return "/" + rel.strip("/") + ("/" if rel.strip("/") else "")


def load_living(path):
    if not path:
        return set()
    j = json.load(open(path, encoding="utf-8"))
    if isinstance(j, dict):
        j = j.get("urls") or j.get("living") or []
    out = set()
    for u in j:
        if isinstance(u, str):
            out.add("/" + u.strip("/") + "/" if u.strip("/") else "/")
    return out


def tracked(path):
    try:
        r = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(path)), "ls-files", "--error-unmatch", os.path.abspath(path)],
                           capture_output=True, text=True)
        return r.returncode == 0
    except OSError:
        return False


def judge(note, snap, rulers=False, seeded_text=None):
    """The failures of one note, as category names (each once). Pure: the self-test drives it. rulers: the archive has opted in to rulers,
    so a note whose snapshot names a ruler must carry it. seeded_text: the archive's own words for a seeded era's note (None: the kit's)."""
    out = []
    m = ID.match(note["id"] or "")
    era = None
    region = None
    if m:
        region, frm = m.group(1), int(m.group(2))
        for e in (snap["regions"].get(region) or []):
            if eralib.numeric(e) and e["from"] == frm and e.get("id") == note["id"]:
                era = e
                break
    if era is None:
        return ["unknown"]
    eras = snap["regions"][region]
    pol = snap["policy"]
    lab = era.get("label") if isinstance(era.get("label"), str) else ""
    lab = lab.strip()
    overlapped = any(o is not era and eralib.numeric(o) and eralib.meets(era, o) for o in eras)
    unassessed = eralib.flag(era.get("approx")) == "unassessed" or eralib.flag(era.get("contested")) == "unassessed"
    y = note["year"]
    yi = int(y) if isinstance(y, str) and re.fullmatch(r"\d{1,4}", y) else None
    mg = eralib.margin_gate(era, yi if yi is not None else era["from"], pol)
    if (mg in ("approx", "contested") or overlapped or not lab or (unassessed and pol["unassessed"] != "allow")):
        out.append("ineligible")
    if mg == "bad-margin" or (mg == "margin" and yi is not None):
        out.append("margin")
    if yi is None or not eralib.covers(era, yi):
        out.append("year")
    elif era["to"] is None and yi >= pol["recent_from"]:
        out.append("recent")
    is_boundary = yi == era["from"] and eralib._has_predecessor(snap, region, eras, era)
    if yi is not None:
        pres = [norm(x) for x in note["pres"]]
        if (is_boundary != (note.get("boundary") == "1") or note.get("boundary") not in (None, "1")
                or (is_boundary and pol["boundary"] != "newer")
                or pres != [norm(eralib.PRE_BOUNDARY if is_boundary else eralib.PRE_NORMAL)]):
            out.append("boundary")
    labs = [norm(x) for x in note["labs"]]
    if len(labs) != 1 or not labs[0] or labs[0] != lab:
        out.append("label")
    if note.get("assessed") != ("1" if era.get("assessed") is True else "0"):
        out.append("assessed")
    if (note.get("approx") != ("1" if eralib.flag(era.get("approx")) == "yes" else None)
            or note.get("contested") != ("1" if eralib.flag(era.get("contested")) == "yes" else None)
            or note.get("unsourced") != ("1" if era.get("margin_sourced") is False and eralib.margin_span(era, eralib.floor_of(pol)) is not None else None)):
        out.append("approx")
    if note.get("edge_agree") not in (None, "1") or (note.get("edge_agree") == "1" and not any(
            snap["places"].get(k) == region for k in (snap.get("edge_neighbours") or {}))):
        out.append("edge")
    seeded = era.get("seeded_from_archive") is True
    want_words = norm(eralib.seeded_words(seeded_text)) if seeded else eralib.SRC_ATLAS
    if note.get("seeded") != ("1" if seeded else None):
        out.append("seeded")
    want_href = eralib.era_href(snap, region, era)
    srcs = [norm(x) for x in note["srcs"]]
    if len(srcs) != 1 or srcs[0] != want_words or want_href is None or note["hrefs"] != [want_href]:
        out.append("source")
    out += rederive(note, snap, region, era, yi, rulers, seeded_text)
    return list(dict.fromkeys(out))


def rederive(note, snap, region, era, yi, rulers, seeded_text=None):
    """Re-derive the whole note from the snapshot, its own place and its year, with the library's own era_at, and hold the note to it: the era, every
    mark missing, extra or wrong, the words, the link and the ruler. -> the category names it fails (the same names as above where one exists)."""
    out = []
    place = note.get("place")
    if not isinstance(place, str) or not place or place != eralib.fold(place) or place not in snap["places"]:
        return ["place"]
    if yi is None:
        return []
    want = eralib.era_at(snap, place, yi)
    if want is None:
        return ["silent"]
    if want["id"] != note["id"] or snap["places"][place] != region:
        return ["place"]
    # the marks, each compared with what the library derives: missing, extra and wrong all fail
    if (note.get("boundary") == "1") != (want["boundary"] is True) or note.get("boundary") not in (None, "1"):
        out.append("boundary")
    if note.get("assessed") != ("1" if want["assessed"] else "0"):
        out.append("assessed")
    if (note.get("approx") != ("1" if want["approx"] else None) or note.get("contested") != ("1" if want["contested"] else None)
            or note.get("unsourced") != ("1" if want["unsourced"] else None)):
        out.append("approx")
    if note.get("edge_agree") != ("1" if want["edgeAgree"] else None):
        out.append("edge")
    if note.get("seeded") != ("1" if want["seeded"] else None):
        out.append("seeded")
    # the ruler: what the library names for this place and year, the Atlas's name exactly, and nothing where it names none
    wr = want["ruler"]
    got = note.get("ruler")
    spans = [norm(x) for x in note.get("rus") or []]
    if got is not None:
        if wr is None or got != wr["name"] or spans != [norm("(%s)" % wr["name"])]:
            out.append("ruler")
    elif spans or (rulers and wr is not None):
        out.append("ruler")
    # the whole text of the note is the snapshot's words: the mark, the label, the ruler (if any), the source, and nothing else
    pre = eralib.PRE_BOUNDARY if want["boundary"] else eralib.PRE_NORMAL
    parts = [pre, want["label"]] + (["(%s)" % wr["name"]] if got is not None and wr is not None else []) + [eralib.seeded_words(seeded_text) if want["seeded"] else want["source"]]
    if norm(note.get("text")) != norm(" ".join(parts)):
        out.append("text")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--living-urls", default=None, help="JSON list of page paths the archive says are living or withheld")
    ap.add_argument("--require-tracked", action="store_true", help="fail if the snapshot is not committed to git")
    ap.add_argument("--min-pages", type=int, default=1)
    ap.add_argument("--min-notes", type=int, default=1)
    ap.add_argument("--rulers", action="store_true",
                    help="the archive has opted in to rulers (EraNote rulers): a note whose snapshot names a ruler for its place and year must carry it")
    ap.add_argument("--seeded-text", default=None,
                    help="the archive's own words for a seeded era's note (EraNote seededText): the gate then requires exactly these; default is the kit's "
                         "\"%s\". Empty, or the plain phrase, is refused" % eralib.SRC_SEEDED)
    ap.add_argument("--strict-unassessed", action="store_true",
                    help="fail a snapshot whose policy keeps eras the Atlas has not assessed (contested/approx null)")
    a = ap.parse_args(argv)
    if a.seeded_text is not None and eralib.seeded_words(a.seeded_text) != " ".join(a.seeded_text.split()):
        ap.error("--seeded-text must be words of the archive's own that are not empty and not the plain \"%s\" (that would read as a second source)" % eralib.SRC_ATLAS)
    dist = outdir.resolve(a.dist)
    line = outdir.note(dist)
    if line:
        print(line)
    try:
        snap = json.load(open(a.snapshot, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("  --    era       COULD NOT READ THE SNAPSHOT (%s). That is not a pass." % type(e).__name__)
        return 2
    try:
        living = load_living(a.living_urls)
    except (OSError, ValueError):
        print("  --    era       COULD NOT READ THE LIVING LIST. That is not a pass.")
        return 2
    pages = scan(dist) if os.path.isdir(dist) else []
    if len(pages) < max(1, a.min_pages):
        print("  --    era       COULD NOT SEE A BUILT SITE (%d page(s) under the build directory). That is not a pass. Build first, "
              "or point ARCHIVE_OUT at the build." % len(pages))
        return 2
    before = outdir.fingerprint(dist)
    fails = {}

    def fail(cat, n=1):
        fails[cat] = fails.get(cat, 0) + n

    shape = check_snapshot(snap)
    if shape:
        fail("snapshot", len(shape))
        print("  FAIL  era       the snapshot is malformed (%d problem(s)); nothing else is checked" % len(shape))
        return 1
    if a.require_tracked and not tracked(a.snapshot):
        fail("untracked")
    n_pages = n_with = n_notes = 0
    seeded_notes = 0
    unassessed_notes = 0
    boundary_notes = 0
    assessed_notes = 0
    edge_notes = 0
    approx_notes = contested_notes = provisional_notes = unsourced_notes = ruler_notes = 0
    css_pages = 0
    for p in pages:
        n_pages += 1
        try:
            html = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "data-era" not in html:
            continue
        pg = Page()
        pg.feed(html)
        pg.close()
        css_pages += 1 if pg.css else 0
        if len(pg.css) != (1 if pg.notes else 0) or any(".era-note" not in c for c in pg.css):
            fail("css")
        if not pg.notes:
            continue
        n_with += 1
        n_notes += len(pg.notes)
        if "noindex" in pg.robots:
            fail("noindex", len(pg.notes))
        if pg.living or url_of(dist, p) in living:
            fail("living", len(pg.notes))
        for note in pg.notes:
            for cat in judge(note, snap, a.rulers, a.seeded_text):
                fail(cat)
            m = ID.match(note["id"] or "")
            if m:
                for e in snap["regions"].get(m.group(1)) or []:
                    if eralib.numeric(e) and e["from"] == int(m.group(2)) and e.get("id") == note["id"]:
                        if e.get("seeded_from_archive") is True:
                            seeded_notes += 1
                        if eralib.flag(e.get("approx")) == "unassessed" or eralib.flag(e.get("contested")) == "unassessed":
                            unassessed_notes += 1
                        if e.get("assessed") is True:
                            assessed_notes += 1
                        if note.get("boundary") == "1":
                            boundary_notes += 1
                        if note.get("edge_agree") == "1":
                            edge_notes += 1
                        if eralib.flag(e.get("approx")) == "yes":
                            approx_notes += 1
                        if eralib.flag(e.get("contested")) == "yes":
                            contested_notes += 1
                        if e.get("margin_src") == "fallback":
                            provisional_notes += 1
                        if note.get("unsourced") == "1":
                            unsourced_notes += 1
                        if note.get("ruler") is not None:
                            ruler_notes += 1
    if outdir.fingerprint(dist) != before:
        print("  --    era       THE BUILD CHANGED WHILE THIS RAN (another build in flight). Results would be noise, so nothing is reported.")
        return 2
    print("  ..    era       %d page(s) read, %d with a note, %d note(s) (%d on an era the Atlas has assessed, %d on one it has not; %d on a "
          "seeded region, %d on a boundary year, %d at an edge where every neighbour agrees; %d on an approximate era and %d on a contested one, "
          "each more than max(N, margin) from the era's bounds with N = %d year(s): %d of them on the PROVISIONAL floor alone (the Atlas gave that era no margin: "
          "not an Atlas fact), %d resting on an UNSOURCED margin (the assessor knew the date but did not find it in a page: softer, N more)); "
          "%d note(s) name a ruler (the Atlas's reign, exactly one covering the year, well inside it%s); %d page(s) carry the era style, one each; "
          "snapshot: contract %s of %s, rings from the %s, %d region(s), %d place(s) (%d not edge-checked, %d at an edge), built %s; policy: "
          "unassessed %s, boundary %s, recent from %s, edge %s, approx %s, contested %s" % (n_pages, n_with, n_notes, assessed_notes, unassessed_notes, seeded_notes,
                                                                 boundary_notes, edge_notes, approx_notes, contested_notes,
                                                                 snap["policy"]["margin_years"], provisional_notes, unsourced_notes, ruler_notes, "; rulers are opted in" if a.rulers else "; rulers are not opted in", css_pages, snap["contract"]["version"],
                                                                 snap["contract"]["generated"], snap["atlas"]["rings_source"], len(snap["regions"]),
                                                                 len(snap["places"]), len(snap["unchecked_edge"]), len(snap["edge_neighbours"]),
                                                                 snap.get("built", "?"), snap["policy"]["unassessed"], snap["policy"]["boundary"],
                                                                 snap["policy"]["recent_from"], snap["policy"]["edge"], snap["policy"]["approx"], snap["policy"]["contested"]))
    if a.strict_unassessed and snap["policy"]["unassessed"] == "allow":
        fail("unassessed-policy")
    if n_notes < a.min_notes:
        print("  --    era       FOUND %d NOTE(S), fewer than --min-notes %d. A gate that saw nothing has not seen that nothing is wrong." %
              (n_notes, a.min_notes))
        return 2
    if fails:
        print("  FAIL  era       %d failure(s): %s" % (sum(fails.values()), ", ".join("%s %d" % kv for kv in sorted(fails.items()))))
        return 1
    print("  ok    era       every note names a contract era the snapshot holds, the year lies inside it (from <= year < to), and no note is on a living or noindex page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
