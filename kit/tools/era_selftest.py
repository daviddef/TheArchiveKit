#!/usr/bin/env python3
"""Prove the era notes' Python half (eralib.py), the snapshot builder (erasnap.py) and the gate (checkera.py) can FAIL.

Invented fixtures only: Ruritania is a country in a novel, and nothing here is a real region, person, date or record.
Every rule of kit/docs/era-notes.md has a planted fault below, and a fault the gate does not catch is a failure of THIS test.

    python3 kit/tools/era_selftest.py
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import eralib  # noqa: E402

CASES = json.load(open(os.path.join(KIT, "data", "era-cases.json"), encoding="utf-8"))
res = []


def case(label, ok, detail=""):
    res.append(bool(ok))
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", label, ("  [" + str(detail)[:300] + "]") if detail and not ok else ""))


def run(script, args):
    env = {k: v for k, v in os.environ.items() if k != "ARCHIVE_OUT"}
    p = subprocess.run([sys.executable, os.path.join(HERE, script)] + args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


# ---------------------------------------------------------------- 1. the Python half agrees with the shared cases
print("eralib.py against the shared cases (the same file era_logic.mjs runs against era.js)")
bad = []
for c in CASES["cases"]:
    s = {"none": None}.get(c.get("snap"), CASES["other_snapshots"].get(c.get("snap")) if c.get("snap") else CASES["snapshot"])
    if c.get("snap") == "none":
        s = None
    got = eralib.era_at(s, c["place"], c["year"])
    why = eralib.why_not(s, c["place"], c["year"])
    if why != c["why"]:
        bad.append(c["id"] + " (why)")
    elif c["want"] is None:
        if got is not None:
            bad.append(c["id"])
    elif got is None or any(got.get(k) != v for k, v in c["want"].items()):
        bad.append(c["id"])
case("all %d era cases give the answers era.js gives" % len(CASES["cases"]), not bad, bad)
bad = [s for s, want in CASES["fold"] if eralib.fold(s) != want]
case("fold agrees on %d spellings" % len(CASES["fold"]), not bad, bad)
bad = [(d, y) for d, y, want in CASES["years"] if eralib.plain_year(d, y) != want]
case("plain_year agrees on %d dates" % len(CASES["years"]), not bad, bad)
bad = [h["id"] for h in CASES["href_cases"] if eralib.region_href({"atlas": {"base": h["base"]}}, "ruritania") != h["href"]]
case("region_href agrees on %d cases" % len(CASES["href_cases"]), not bad, bad)

tmp = tempfile.mkdtemp(prefix="era-")

# ---------------------------------------------------------------- 2. erasnap.py
print("erasnap.py: what it keeps, what it refuses, what it counts")
ATLAS = {
    "regimes": {
        "kingdom": {"label": "Kingdom of Ruritania"},
        "republic": {"label": "Republic of Ruritania"},
        "feudal": {"label": "Dukes and Counts"},
        "nameless": {},
        "brief": {"label": "The Short Republic", "existed": [1900, 1920]},
    },
    "regions": [
        {"id": "ruritania", "ring": [[0, 10], [0, 20], [10, 20], [10, 10]], "eras": [
            {"from": 1000, "to": 1700, "regime": "feudal"},
            {"from": 1700, "to": 1800, "regime": "kingdom"},
            {"from": 1800, "to": 1850, "regime": "kingdom", "approx": True},
            {"from": 1850, "to": "c. 1900", "regime": "republic"},
            {"from": 1900, "to": 1910, "regime": "nameless"},
            {"from": 1910, "to": 1900, "regime": "kingdom"},
            {"from": 1900, "to": 1950, "regime": "brief"},
            {"from": 1950, "to": 1990, "regime": "kingdom"},
            {"from": 1980, "to": 2000, "regime": "republic"},
        ]},
        {"id": "elphberg", "ring": [[20, 10], [20, 20], [30, 20], [30, 10]], "eras": [
            {"from": 1700, "to": 1800, "regime": "kingdom"}]},
        {"id": "unused", "ring": [[40, 10], [40, 20], [50, 20], [50, 10]], "eras": [
            {"from": 1700, "to": 1800, "regime": "kingdom"}]},
    ],
}
ap = os.path.join(tmp, "regions.json")
json.dump(ATLAS, open(ap, "w"))
table = {"places": {"Hentzau": {"region": "ruritania", "lat": 5, "lon": 15}, "HENTZAU!": "ruritania", "Edge Town": {"region": "ruritania", "lat": 25, "lon": 15},
                    "Far Hill": {"region": "ruritania", "lat": 60, "lon": 60}, "Zenda": "elphberg", "Nowhere": None, "Dash": "-"}}
tp = os.path.join(tmp, "places.json")
json.dump(table, open(tp, "w"))
out = os.path.join(tmp, "snap.json")
base = ["--atlas", ap, "--places", tp, "--out", out, "--atlas-ref", "abc1234", "--built", "2026-01-01"]
c, o = run("erasnap.py", base + ["--seeded", "elphberg"])
snap = json.load(open(out)) if c == 0 else {}
case("it builds a snapshot from an Atlas file and an archive's place table", c == 0 and snap.get("version") == 1, o)
case("it says which Atlas it came from (reference and the file's hash)", snap.get("atlas_commit_or_etag") == "abc1234" and len(snap.get("atlas", {}).get("file_sha256", "")) == 64, snap.get("atlas"))
case("only the regions the archive's table uses are kept", sorted(snap.get("regions", {})) == ["elphberg", "ruritania"], list(snap.get("regions", {})))
eras = snap.get("regions", {}).get("ruritania", [])
case("a words-only end, an inverted span, an empty label, a shorthand regime and an era outside its regime's dates are refused (5)",
     sorted((d["from"], d["reason"].split()[0]) for d in snap.get("dropped", []) if d["region"] == "ruritania") ==
     sorted([(1000, "regime"), (1850, "words-only"), (1900, "regime"), (1910, "start"), (1900, "era")]), snap.get("dropped"))
case("the kept eras are the four with real years and a label", [(e["from"], e["to"]) for e in eras] == [(1700, 1800), (1800, 1850), (1950, 1990), (1980, 2000)], eras)
case("an approximate era is kept and flagged", [e["approx"] for e in eras] == [False, True, False, False])
case("two overlapping eras are both kept and both flagged contested", [e["contested"] for e in eras] == [False, False, True, True], eras)
case("a region the Atlas seeded from the archive's own research is flagged on every era", all(e["seeded_from_archive"] for e in snap["regions"]["elphberg"]) and not any(e["seeded_from_archive"] for e in eras))
case("only the regimes the kept eras use, with their labels", snap.get("regimes") == {"kingdom": "Kingdom of Ruritania", "republic": "Republic of Ruritania"}, snap.get("regimes"))
pk = snap.get("places", {})
case("two spellings of one place are one key; a null or dash region is not a place", sorted(pk) == ["far hill", "hentzau", "zenda"], sorted(pk))
case("a place whose coordinates fall in ANOTHER region's ring, and not its own, is refused; one in no ring is kept", "edge town" not in pk and "far hill" in pk, sorted(pk))
case("what it built answers as the library does", (eralib.era_at(snap, "Hentzau", 1750) or {}).get("label") == "Kingdom of Ruritania"
     and eralib.era_at(snap, "Hentzau", 1825) is None and eralib.era_at(snap, "Hentzau", 1985) is None and eralib.era_at(snap, "Zenda", 1750)["seeded"] is True)
case("the output tells the counts and names no place", "places_refused_ring" in o and "Hentzau" not in o and "Edge" not in o, o)
c2, o2 = run("erasnap.py", base + ["--seeded", "elphberg", "--check"])
case("--check passes on a snapshot rebuilt from the same inputs", c2 == 0, o2)
s2 = json.load(open(out))
s2["regions"]["ruritania"][0]["regime"] = "republic"
json.dump(s2, open(out, "w"))
c2, o2 = run("erasnap.py", base + ["--seeded", "elphberg", "--check"])
case("--check fails on a snapshot edited by hand", c2 == 1, o2)
json.dump(snap, open(out, "w"))
json.dump({"places": {"Hentzau": "narnia"}}, open(tp, "w"))
c2, o2 = run("erasnap.py", base)
case("a place sent to a region the Atlas does not hold stops the build", c2 != 0 and "narnia" in o2, o2)
json.dump({"places": {"Hentzau": "ruritania", "hentzau": "elphberg"}}, open(tp, "w"))
c2, o2 = run("erasnap.py", base)
case("two spellings of one place sent to two regions stop the build", c2 != 0, o2)
json.dump(table, open(tp, "w"))
c2, o2 = run("erasnap.py", ["--atlas", ap, "--places", tp, "--out", out])
case("no reference to the Atlas, and no git history to take one from, is refused", c2 == 2, o2)

# ---------------------------------------------------------------- 3. checkera.py
print("checkera.py: a planted fault for each rule")
CLEAN = CASES["gate_snapshot"]


def lab_of(snap, region, frm):
    e = next(x for x in snap["regions"][region] if x["from"] == frm)
    return snap["regimes"][e["regime"]]


def note(id_="ruritania--1700", year="1750", label="Kingdom of Ruritania", src="per the Record Atlas", href="https://atlas.example.test/region/ruritania/"):
    a = '<a class="era-src" href="%s" rel="noopener">%s</a>' % (href, src) if href else '<span class="era-src">%s</span>' % src
    return ('<span class="era-note" data-era="%s" data-era-year="%s"><span class="era-pre">· At the time: </span>'
            '<span class="era-lab">%s</span> %s</span>' % (id_, year, label, a))


def page(body, head="", attrs=""):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>A page</title>%s</head><body %s><main><h1>A person</h1>'
            '<div class="v">Hentzau%s</div></main></body></html>' % (head, attrs, body))


def gate(pages, snap=CLEAN, extra=None, snap_text=None, name="g"):
    d = os.path.join(tmp, name)
    os.makedirs(d, exist_ok=True)
    dist = os.path.join(d, "dist")
    if os.path.isdir(dist):
        import shutil
        shutil.rmtree(dist)
    for rel, html in pages.items():
        p = os.path.join(dist, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(html)
    if not pages:
        os.makedirs(dist, exist_ok=True)
    sp = os.path.join(d, "era-snapshot.json")
    open(sp, "w").write(snap_text if snap_text is not None else json.dumps(snap))
    return run("checkera.py", ["--dist", dist, "--snapshot", sp] + (extra or []))


P = "people/a/index.html"
c, o = gate({P: page(note())})
case("control: a note the snapshot supports passes (exit 0)", c == 0 and "1 note(s)" in o, o)
c, o = gate({P: page(note()), "people/b/index.html": page(note("elphberg--1900", "1975", "Kingdom of Ruritania", "per this archive's own research",
                                                                "https://atlas.example.test/region/elphberg/"))})
case("control: a note on a seeded region that says so passes, and is counted as seeded", c == 0 and "(1 on a seeded region)" in o, o)


def fails(label, pages, cat, snap=CLEAN, extra=None, code=1, snap_text=None):
    c, o = gate(pages, snap, extra, snap_text)
    case(label, c == code and (cat is None or cat in o), "exit %s: %s" % (c, o))


print("  rule a/b: a note must name an era the snapshot holds")
fails("a (region, from) pair that is not an era", {P: page(note("ruritania--1701"))}, "unknown 1")
fails("a region the snapshot lacks", {P: page(note("narnia--1700"))}, "unknown 1")
fails("a data-era that is not of the shape region--year", {P: page(note("ruritania"))}, "unknown 1")
s = copy.deepcopy(CLEAN)
fails("an era the snapshot flags approximate", {P: page(note("ruritania--1800", "1820", "Occupied Ruritania"))}, "ineligible 1", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["contested"] = True
fails("an era the snapshot flags contested", {P: page(note())}, "ineligible 1", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"].append({"from": 1790, "to": 1810, "regime": "republic", "approx": False, "contested": False, "seeded_from_archive": False, "sources": []})
fails("an era that overlaps another of its region", {P: page(note())}, "ineligible 1", s)
s = copy.deepcopy(CLEAN); s["regimes"]["kingdom"] = "  "
fails("an era whose regime has no label (the snapshot is refused as malformed first)", {P: page(note(label=""))}, None, s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["to"] = "c. 1800"
fails("an era with a words-only end (malformed snapshot)", {P: page(note())}, "malformed", s)
print("  rule d: the year must lie strictly inside the era")
fails("a year after the era", {P: page(note(year="1800"))}, "year 1")
fails("a year on the era's first year", {P: page(note(year="1700"))}, "year 1")
fails("a year before the era", {P: page(note(year="1650"))}, "year 1")
fails("no year on the note", {P: page(note().replace(' data-era-year="1750"', ""))}, "year 1")
fails("a year that is not a number", {P: page(note(year="about 1750"))}, "year 1")
print("  words: the label and the source")
fails("a label that differs from the snapshot's regime label", {P: page(note(label="Empire of Ruritania"))}, "label 1")
fails("a note with no label", {P: page(note().replace('<span class="era-lab">Kingdom of Ruritania</span>', ""))}, "label 1")
fails("a note that does not say where it came from", {P: page(note(src="at the time"))}, "source 1")
fails("a seeded region's note that says 'per the Record Atlas' (rule f)", {P: page(note("elphberg--1900", "1975", "Kingdom of Ruritania", "per the Record Atlas", "https://atlas.example.test/region/elphberg/"))}, "source 1")
fails("a link that is not the Atlas's page for the region (rule e)", {P: page(note(href="https://elsewhere.example.test/"))}, "source 1")
fails("a source with no link at all", {P: page(note(href=None))}, "source 1")
print("  rule c: no note on a living, held-out or noindex page")
fails("a note on a page that says noindex", {P: page(note(), '<meta name="robots" content="noindex, nofollow">')}, "noindex 1")
fails("a note on a page marked living", {P: page(note(), attrs='data-living="1"')}, "living 1")
print("  the gate must see something")
fails("no built site at all is not a pass (exit 2)", {}, "COULD NOT SEE A BUILT SITE", code=2)
fails("a site with pages and no note is not a pass (exit 2)", {P: page("")}, "FOUND 0 NOTE", code=2)
fails("an unreadable snapshot is not a pass (exit 2)", {P: page(note())}, "COULD NOT READ THE SNAPSHOT", code=2, snap_text="{ not json")
fails("a snapshot of another version is malformed", {P: page(note())}, "malformed", dict(CLEAN, version=2))
s = copy.deepcopy(CLEAN); s["atlas_commit_or_etag"] = ""
fails("a snapshot that does not say which Atlas it came from is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["places"]["x"] = "narnia"
fails("a place sent to a region the snapshot lacks is malformed", {P: page(note())}, "malformed", s)
fails("a snapshot outside git, with --require-tracked", {P: page(note())}, "failure(s): untracked 1", extra=["--require-tracked"])

# the living list needs the real path of the page: rewrite the placeholder
d = os.path.join(tmp, "g2")
os.makedirs(d, exist_ok=True)
lv = os.path.join(d, "living.json")
json.dump(["/people/a/"], open(lv, "w"))
c, o = gate({P: page(note())}, extra=["--living-urls", lv], name="g2")
case("a note on a page the archive's living list names (list read)", c == 1 and "living 1" in o, o)
c, o = gate({P: page(note()), "people/b/index.html": page(note())}, extra=["--living-urls", lv], name="g2")
case("only the listed page fails; the other page's note is counted fine", c == 1 and "living 1" in o and "2 note(s)" in o, o)
c, o = gate({P: page(note())}, extra=["--living-urls", os.path.join(d, "nope.json")], name="g2")
case("an unreadable living list is not a pass (exit 2)", c == 2, o)
# the printed output carries counts only
c, o = gate({P: page(note(label="Empire of Ruritania"))}, name="g3")
case("the output names no place, no label, no year", "Hentzau" not in o and "Ruritania" not in o and "1750" not in o and "people/a" not in o, o)
# a tracked snapshot
rd = os.path.join(tmp, "repo")
os.makedirs(rd)
subprocess.run(["git", "init", "-q", rd], check=True)
subprocess.run(["git", "-C", rd, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "x"], check=True)
sp = os.path.join(rd, "era-snapshot.json")
json.dump(CLEAN, open(sp, "w"))
dist = os.path.join(rd, "dist")
os.makedirs(os.path.join(dist, "people", "a"))
open(os.path.join(dist, "people", "a", "index.html"), "w").write(page(note()))
c, o = run("checkera.py", ["--dist", dist, "--snapshot", sp, "--require-tracked"])
case("--require-tracked: a snapshot in a repository but not committed fails", c == 1 and "untracked 1" in o, o)
subprocess.run(["git", "-C", rd, "add", "era-snapshot.json"], check=True)
c, o = run("checkera.py", ["--dist", dist, "--snapshot", sp, "--require-tracked"])
case("--require-tracked: once it is added, it passes", c == 0, o)

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
print("\n%s" % ("  ok    %d checks: the Python half, the snapshot builder, and a planted fault for each rule" % len(res) if all(res)
                else "%d of %d FAILED" % (res.count(False), len(res))))
sys.exit(0 if all(res) else 1)
