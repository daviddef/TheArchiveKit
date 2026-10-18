#!/usr/bin/env python3
"""The gate behind the "at the time" notes: does every note a BUILT site prints say only what the snapshot supports?

kit/components/EraNote.astro draws `<span class="era-note" data-era="<region>--<from>" data-era-year="<year>">`. This reads the
built HTML (not the template: a template that is right can still be fed a wrong year) and the era snapshot the archive commits,
and fails on:

  snapshot   the snapshot itself is malformed: wrong version, no atlas reference, a place sent to a region it does not hold, an
             era without whole-number years, a regime without a label
  untracked  (--require-tracked) the snapshot is not committed: a build from a checkout would not have it
  noindex    a note on a page that says noindex (a living, held-out or withheld person's page: rule c)
  living     a note on a page marked data-living, or listed in --living-urls (the archive's own living list)
  unknown    a note whose (region, from) pair is not an era in the snapshot, or whose data-era is not of that shape
  ineligible a note on an era the snapshot itself flags approximate or contested, that overlaps another era of its region, or whose
             regime has no label: the library would never have drawn it (rule b)
  year       a note whose data-era-year is missing, not a whole number, or not strictly inside the era (a year ON a boundary is
             outside: rule d)
  label      a note whose words differ from the snapshot's label for the era's regime, or that has no label, or two
  source     a note that does not say where it came from ("per the Record Atlas", or "per this archive's own research" for a
             region the snapshot marks seeded_from_archive: rule f), or whose link is not the Atlas's page for that region (rule e)

It prints COUNTS ONLY: never a place, a person, a date or a path. ZERO PAGES EXAMINED IS NOT A PASS, and neither are zero notes
(--min-notes, default 1): a gate that found nothing because it looked in the wrong place has not found that nothing is wrong. It
reads the tree twice and throws its results away if the tree changed while it ran (another build in flight). ARCHIVE_OUT beats
--dist, as everywhere in this kit (outdir.py).

    python3 checkera.py --dist dist --snapshot src/data/era-snapshot.json [--living-urls living.json] [--require-tracked]
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

ID = re.compile(r"^([a-z0-9][a-z0-9-]*)--(\d{1,4})$")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.robots = ""
        self.living = False
        self.notes = []
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
        note = None
        part = None
        if "data-era" in a:
            note = {"id": a["data-era"], "year": a.get("data-era-year"), "labs": [], "srcs": [], "hrefs": []}
            self.notes.append(note)
            self.cur = note
        elif self.cur is not None:
            if "era-lab" in cls:
                part = "lab"
                self.cur["labs"].append("")
            if "era-src" in cls:
                part = "src"
                self.cur["srcs"].append("")
                self.cur["hrefs"].append(a.get("href"))
        if tag not in VOID:
            self.stack.append((tag, note, part))

    def handle_endtag(self, tag):
        while self.stack:
            t, note, part = self.stack.pop()
            if note is not None and self.cur is note:
                self.cur = None
            if t == tag:
                break

    def handle_data(self, data):
        if self.cur is None:
            return
        for t, note, part in reversed(self.stack):
            if part == "lab":
                self.cur["labs"][-1] += data
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
    if not isinstance(snap.get("atlas_commit_or_etag"), str) or not snap["atlas_commit_or_etag"].strip():
        bad.append("no atlas reference")
    if eralib.region_href(snap, "x") is None:
        bad.append("no usable atlas base")
    if not isinstance(snap.get("regions"), dict) or not isinstance(snap.get("places"), dict) or not isinstance(snap.get("regimes"), dict):
        return bad + ["regions, places or regimes missing"]
    for k, r in snap["places"].items():
        if k != eralib.fold(k) or not k:
            bad.append("a place key is not folded")
        if r not in snap["regions"]:
            bad.append("a place goes to a region the snapshot lacks")
    for rid, eras in snap["regions"].items():
        if not isinstance(eras, list):
            bad.append("a region's eras are not a list")
            continue
        for e in eras:
            if not eralib.numeric(e):
                bad.append("an era without whole-number years")
            elif not isinstance(snap["regimes"].get(e.get("regime")), str) or not snap["regimes"][e["regime"]].strip():
                bad.append("an era whose regime has no label")
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


def judge(note, snap):
    """The failures of one note, as category names. Pure: the self-test drives it."""
    out = []
    m = ID.match(note["id"] or "")
    era = None
    region = None
    if m:
        region, frm = m.group(1), int(m.group(2))
        for e in (snap["regions"].get(region) or []):
            if eralib.numeric(e) and e["from"] == frm:
                era = e
                break
    if era is None:
        return ["unknown"]
    eras = snap["regions"][region]
    lab = (snap["regimes"].get(era.get("regime")) or "")
    lab = lab.strip() if isinstance(lab, str) else ""
    flagged = lambda k: k in era and era[k] is not False
    overlapped = any(o is not era and eralib.numeric(o) and o["from"] < era["to"] and era["from"] < o["to"] for o in eras)
    if flagged("approx") or flagged("contested") or overlapped or not lab:
        out.append("ineligible")
    y = note["year"]
    if not (isinstance(y, str) and re.fullmatch(r"\d{1,4}", y)) or not (era["from"] < int(y) < era["to"]):
        out.append("year")
    labs = [norm(x) for x in note["labs"]]
    if len(labs) != 1 or not labs[0] or labs[0] != lab:
        out.append("label")
    seeded = era.get("seeded_from_archive") is True
    want_words = eralib.SRC_OWN if seeded else eralib.SRC_ATLAS
    want_href = eralib.region_href(snap, region)
    srcs = [norm(x) for x in note["srcs"]]
    if len(srcs) != 1 or srcs[0] != want_words or note["hrefs"] != [want_href]:
        out.append("source")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--living-urls", default=None, help="JSON list of page paths the archive says are living or withheld")
    ap.add_argument("--require-tracked", action="store_true", help="fail if the snapshot is not committed to git")
    ap.add_argument("--min-pages", type=int, default=1)
    ap.add_argument("--min-notes", type=int, default=1)
    a = ap.parse_args(argv)
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
        if not pg.notes:
            continue
        n_with += 1
        n_notes += len(pg.notes)
        if "noindex" in pg.robots:
            fail("noindex", len(pg.notes))
        if pg.living or url_of(dist, p) in living:
            fail("living", len(pg.notes))
        for note in pg.notes:
            for cat in judge(note, snap):
                fail(cat)
            m = ID.match(note["id"] or "")
            if m:
                for e in snap["regions"].get(m.group(1)) or []:
                    if eralib.numeric(e) and e["from"] == int(m.group(2)) and e.get("seeded_from_archive") is True:
                        seeded_notes += 1
    if outdir.fingerprint(dist) != before:
        print("  --    era       THE BUILD CHANGED WHILE THIS RAN (another build in flight). Results would be noise, so nothing is reported.")
        return 2
    print("  ..    era       %d page(s) read, %d with a note, %d note(s) (%d on a seeded region); snapshot: %d region(s), %d place(s), "
          "built %s" % (n_pages, n_with, n_notes, seeded_notes, len(snap["regions"]), len(snap["places"]), snap.get("built", "?")))
    if n_notes < a.min_notes:
        print("  --    era       FOUND %d NOTE(S), fewer than --min-notes %d. A gate that saw nothing has not seen that nothing is wrong." %
              (n_notes, a.min_notes))
        return 2
    if fails:
        print("  FAIL  era       %d failure(s): %s" % (sum(fails.values()), ", ".join("%s %d" % kv for kv in sorted(fails.items()))))
        return 1
    print("  ok    era       every note names an era the snapshot holds, the year lies inside it, and no note is on a living or noindex page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
