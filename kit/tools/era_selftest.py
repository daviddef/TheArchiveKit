#!/usr/bin/env python3
"""Prove the era notes' Python half (eralib.py), the snapshot builder (erasnap.py) and the gate (checkera.py) can FAIL.

Invented fixtures only: Ruritania is a country in a novel, and nothing here is a real region, person, date or record.
Every rule of kit/docs/era-notes.md has a planted fault below, and a fault the gate does not catch is a failure of THIS test.

    python3 kit/tools/era_selftest.py
"""
import copy
import hashlib
import json
import math
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


def snap_of(c):
    k = c.get("snap")
    return None if k == "none" else CASES["other_snapshots"][k] if k else CASES["snapshot"]


def failing(lib):
    """The ids of the shared cases a library (the real one, or a copy with one rule broken) gets wrong."""
    out = []
    for c in CASES["cases"]:
        s = copy.deepcopy(snap_of(c))
        rf = (c.get("opts") or {}).get("recent_from")
        try:
            got = lib.era_at(s, c["place"], c["year"], rf)
            why = lib.why_not(s, c["place"], c["year"], rf)
        except Exception as e:  # noqa: BLE001
            out.append(c["id"] + " (threw %s)" % type(e).__name__)
            continue
        if why != c["why"]:
            out.append(c["id"] + " (why)")
        elif c["want"] is None:
            if c["why"] == "ok" or got is not None:
                out.append(c["id"])
        elif got is None or any(got.get(k) != v for k, v in c["want"].items()):
            out.append(c["id"])
    return out


# ---------------------------------------------------------------- 1. the Python half agrees with the shared cases
print("eralib.py against the shared cases (the same file era_logic.mjs runs against era.js)")
bad = failing(eralib)
case("all %d era cases give the answers era.js gives" % len(CASES["cases"]), not bad, bad)
bad = [s for s, want in CASES["fold"] if eralib.fold(s) != want]
case("fold agrees on %d spellings" % len(CASES["fold"]), not bad, bad)
bad = [(d, y) for d, y, want in CASES["years"] if eralib.plain_year(d, y) != want]
case("plain_year agrees on %d dates" % len(CASES["years"]), not bad, bad)
bad = [h["id"] for h in CASES["href_cases"] if eralib.region_href({"atlas": {"base": h["base"]}}, "ruritania") != h["href"]]
case("region_href agrees on %d cases" % len(CASES["href_cases"]), not bad, bad)

print("eralib.py: a planted fault for each rule is caught by the shared cases")
src = open(os.path.join(HERE, "eralib.py"), encoding="utf-8").read()
FAULTS = [
    ("the end year of an era is inside it (closed interval)", 'return e["from"] <= year and (is_open(e) or year < e["to"])',
     'return e["from"] <= year and (is_open(e) or year <= e["to"])', "the-year-an-era-ends-belongs-to-the-next-era"),
    ("a still-running era covers nothing", 'return e["from"] <= year and (is_open(e) or year < e["to"])',
     'return e["from"] <= year and year < e["to"]', "accents-and-case-are-folded"),
    ("a missing end is taken for a still-running era", 'return isinstance(e, dict) and "to" in e and e["to"] is None',
     'return isinstance(e, dict) and e.get("to") is None', "an-era-with-no-end-at-all-is-not-still-running"),
    ("a boundary year takes the newer era whatever the snapshot says", 'if pol.get("boundary") != "newer":\n            return no("boundary")',
     'if False:\n            return no("boundary")', "a-boundary-year-is-silent-when-the-snapshot-does-not-say-newer"),
    ("a boundary year is not noticed", 'if year == e["from"] and _has_predecessor(snap, region, eras, e):',
     'if False and _has_predecessor(snap, region, eras, e):', "a-boundary-year-takes-the-newer-era-and-says-so"),
    ("a refused predecessor does not make a boundary", 'return any(drop_ok(d) and d.get("region") == region and d.get("to") == e["from"] for d in (snap.get("dropped") or []))',
     "return False", "a-boundary-after-a-refused-era-still-says-so"),
    ("the quiet rule is off", 'if is_open(e) and year >= recent_from:\n        return no("recent")', "if False:\n        return no(\"recent\")", "the-quiet-rule-1990"),
    ("the quiet rule starts a year late", "year >= recent_from", "year > recent_from", "the-quiet-rule-1990"),
    ("the quiet rule touches closed eras", "if is_open(e) and year >= recent_from:", "if year >= recent_from:", "the-quiet-rule-never-touches-a-closed-era"),
    ("the caller's quiet-rule year is ignored", "if recent_from is None:\n        recent_from =", "if True:\n        recent_from =", "the-quiet-rule-can-be-moved-by-the-caller"),
    ("the snapshot's quiet-rule year is ignored", 'recent_from = pol["recent_from"] if is_year(pol.get("recent_from")) else RECENT_FROM',
     "recent_from = RECENT_FROM", "the-quiet-rule-can-be-moved-by-the-snapshot"),
    ("null is taken for false", 'return "unassessed" if v is None else "yes"', 'return "no" if v is None else "yes"', "an-era-with-null-flags-is-unassessed"),
    ("an unassessed era is noted whatever the policy says", 'if unassessed and pol.get("unassessed") != "allow":\n        return no("unassessed")',
     "if False:\n        return no(\"unassessed\")", "an-era-with-null-flags-is-unassessed"),
    ("an unassessed era is never allowed", 'if unassessed and pol.get("unassessed") != "allow":', "if unassessed:",
     "an-era-with-null-flags-is-allowed-when-the-snapshot-says-so"),
    ("a flag that is neither true, false nor null counts as false", 'return "unassessed" if v is None else "yes"', 'return "unassessed" if v is None else "no"',
     "a-flag-that-is-neither-true-false-nor-null-is-silent-even-when-allowing"),
    ("an approximate era gets a note", 'if flag(e.get("approx")) == "yes":\n        return no("approx")', 'if False:\n        return no("approx")', "an-approximate-era-is-silent"),
    ("an era that overlaps another is not contested", "or any(e.get(\"contested\") is True or any(o is not e and numeric(o) and meets(e, o) for o in eras)\n                                           for e in covering)",
     "or any(e.get(\"contested\") is True for e in covering)", "an-era-that-overlaps-another-is-silent-even-where-it-stands-alone"),
    ("a refused era overlapping a kept one is ignored", "if len(covering) > 1 or refused or any(", "if len(covering) > 1 or any(", "a-refused-era-overlapping-a-kept-one-is-silent"),
    ("an empty label is allowed", 'if not _label(e):\n        return no("no-label")', 'if False:\n        return no("no-label")', "an-empty-regime-label-is-silent"),
    ("an era whose id is not the contract's is allowed", 'if e.get("id") != era_id(region, e["from"]):\n        return no("bad-id")', 'if False:\n        return no("bad-id")',
     "an-era-whose-id-is-not-the-contracts-is-silent"),
    ("any url is a link", 'return b + e["url"] if e["url"] == "/region/%s/#era-%s" % (region, e.get("from")) else None', 'return b + e["url"]',
     "an-era-keeps-the-link-the-contract-gives-only-if-it-is-its-own"),
    ("a refused era is reported as no era", 'return no("era-refused" if refused else "no-era")', 'return no("no-era")', "a-refused-era-is-silent-and-counted-as-refused"),
    ("a place on the edge is not silent", "if isinstance(silent, dict) and silent.get(key) in VALID_SILENT:\n        return no(silent[key])",
     "if False:\n        return no(silent[key])", "a-place-on-the-edge-is-silent"),
    ("any silence reason is believed", "isinstance(silent, dict) and silent.get(key) in VALID_SILENT", "isinstance(silent, dict) and key in silent", "an-unknown-silence-reason-is-no-region"),
    ("an unchecked place is not flagged", '"unchecked": d["key"] in (snap.get("unchecked_edge") or [])', '"unchecked": False', "a-place-that-could-not-be-edge-checked-is-flagged"),
    ("a snapshot of another version is read", 'snap.get("version") != VERSION', "False", "a-snapshot-of-the-first-version-is-refused"),
    ("a seeded era is not marked", 'seeded = e.get("seeded_from_archive") is True', "seeded = False", "accents-and-case-are-folded"),
    ("a near-edge place is noted whatever its neighbours say", 'if kind is None or not lst or any(nb == region or not _neighbour_agrees(snap, nb, year, e, boundary, pol) for nb in lst):\n            return no(kind or "edge")',
     "if False:\n            return no(kind or \"edge\")", "a-place-near-an-edge-is-silent-where-its-neighbour-has-another-regime"),
    ("a near-edge place needs only ONE agreeing neighbour", "any(nb == region or not _neighbour_agrees(", "all(nb == region or not _neighbour_agrees(",
     "a-place-near-an-edge-is-silent-where-any-one-neighbour-differs"),
    ("a near-edge place with no neighbours is noted", "if kind is None or not lst or any(", "if kind is None or any(", "an-edge-place-with-no-neighbours-is-silent"),
    ("an unknown kind of edge is believed", "if kind is None or not lst or any(", "if not lst or any(", "an-edge-place-with-a-kind-the-library-does-not-know-is-silent"),
    ("a region is its own neighbour", "any(nb == region or not _neighbour_agrees(", "any(not _neighbour_agrees(", "an-edge-place-that-names-its-own-region-as-neighbour-is-silent"),
    ("a ring conflict is reported as an edge", 'return no(kind or "edge")', 'return no("edge")', "a-place-in-a-neighbours-ring-is-silent-as-a-ring-conflict-where-they-differ"),
    ("the edge agreement is not recorded on the era", '"edgeAgree": d["edge_agree"]', '"edgeAgree": False', "a-place-near-an-edge-keeps-its-note-where-its-neighbour-has-the-same-regime"),
    ("the assessed flag is not recorded on the era", '"assessed": not d["unassessed"]', '"assessed": True', "an-era-with-null-flags-is-allowed-when-the-snapshot-says-so"),
    ("a neighbour the snapshot does not hold is trusted", "if not isinstance(nb, str) or not isinstance(regions, dict) or not isinstance(regions.get(nb), list):\n        return False",
     "if not isinstance(nb, str) or not isinstance(regions, dict) or not isinstance(regions.get(nb), list):\n        return True", "a-neighbour-the-snapshot-does-not-hold-is-unknown"),
    ("a neighbour with a refused era over the year is trusted", "if any(covers(d, year) for d in dropped):\n        return False", "", "a-neighbour-with-a-refused-era-over-the-year-is-silent"),
    ("a neighbour with no era for the year is trusted", "if len(covering) != 1:\n        return False\n    x = covering[0]", "if len(covering) > 1:\n        return False\n    x = covering[0] if covering else mine",
     "a-place-near-an-edge-is-silent-where-its-neighbour-has-no-era-for-the-year"),
    ("a neighbour era that overlaps another elsewhere is trusted", "if any(o is not x and numeric(o) and meets(x, o) for o in eras):\n        return False\n    if flag(x.get(\"approx\"))",
     "if flag(x.get(\"approx\"))", "a-neighbour-era-that-overlaps-another-anywhere-is-silent"),
    ("a neighbour era marked approximate is trusted", 'if flag(x.get("approx")) == "yes" or flag(x.get("contested")) == "yes":\n        return False', 'if flag(x.get("contested")) == "yes":\n        return False',
     "a-place-near-an-edge-is-silent-where-its-neighbour-era-is-approximate"),
    ("a neighbour era marked contested is trusted", 'if flag(x.get("approx")) == "yes" or flag(x.get("contested")) == "yes":\n        return False', 'if flag(x.get("approx")) == "yes":\n        return False',
     "a-neighbour-marked-contested-is-silent"),
    ("a neighbour the Atlas has not assessed is trusted whatever the policy says", 'and pol.get("unassessed") != "allow":\n        return False\n    if _label(x)', "and False:\n        return False\n    if _label(x)",
     "a-neighbour-the-atlas-has-not-assessed-is-unknown-under-the-refuse-policy"),
    ("a neighbour the Atlas has not assessed is never allowed", 'and pol.get("unassessed") != "allow":\n        return False\n    if _label(x)', "and True:\n        return False\n    if _label(x)",
     "a-neighbour-the-atlas-has-not-assessed-is-allowed-when-the-snapshot-says-so"),
    ("a neighbour's label need not be the same words", "if _label(x) != _label(mine):", "if _label(x).lower() != _label(mine).lower():", "a-neighbour-label-must-be-the-same-words"),
    ("any neighbour regime is agreement", "if _label(x) != _label(mine):\n        return False", "", "a-place-near-an-edge-is-silent-where-its-neighbour-has-another-regime"),
    ("a neighbour's change in the year is not looked at", "if not boundary and year == x[\"from\"]:", "if False:", "a-neighbour-whose-era-begins-this-year-after-another-regime-is-silent"),
    ("a neighbour's change is looked at even for a boundary note", "if not boundary and year == x[\"from\"]:", "if year == x[\"from\"]:", "a-boundary-note-needs-only-the-neighbours-newer-era"),
    ("a neighbour with no era before its first is trusted", "if not before or any(", "if any(", "a-neighbour-whose-first-era-begins-this-year-is-unknown-before-it"),
    ("a neighbour's refused predecessor is ignored", 'if any(d.get("to") == year for d in dropped):\n            return False', "", "a-neighbour-whose-predecessor-was-refused-is-unknown"),
    ("a neighbour's predecessor may have another label", "if not before or any(_label(o) != _label(mine) or", "if not before or any(False or", "a-neighbour-whose-era-begins-this-year-after-another-regime-is-silent"),
]
for label, a, b, must in FAULTS:
    if a not in src:
        case("planted fault '%s' could be planted (the code changed)" % label, False)
        continue
    ns = {}
    code = compile(src.replace(a, b, 1), "eralib_broken", "exec")
    exec(code, ns)  # noqa: S102 - our own source, one rule broken

    class Lib:
        era_at = staticmethod(ns["era_at"])
        why_not = staticmethod(ns["why_not"])
    f = failing(Lib)
    case("planted fault '%s' is caught (%s)" % (label, must), any(x.startswith(must) for x in f), f[:3])

# geometry
print("eralib.py: the ring-edge distance")
RING = [[0, 10], [0, 20], [10, 20], [10, 10]]
d = eralib.edge_km(5, 15, RING)
case("a point in the middle of a 10 degree square is about 554 km from the nearest edge", abs(d - 553.8) < 6, d)
d = eralib.edge_km(0.1, 15, RING)
case("a point 0.1 degree inside the south edge is about 11 km from it", abs(d - 11.12) < 0.3, d)
d = eralib.edge_km(-0.1, 15, RING)
case("a point 0.1 degree OUTSIDE the south edge is also about 11 km from it", abs(d - 11.12) < 0.3 and not eralib.pip(-0.1, 15, RING), d)
d = eralib.edge_km(5, 10.05, RING)
case("a point near the west edge measures in km of longitude (cos latitude), not degrees", abs(d - 0.05 * 111.195 * math.cos(math.radians(5))) < 0.2, d)
case("a point near a vertex is measured to the vertex, not to the edge's line beyond it", abs(eralib.edge_km(-0.1, 9.9, RING) - math.hypot(0.1 * 111.195, 0.1 * 111.195 * math.cos(math.radians(-0.1)))) < 0.5)
case("pip: inside and outside", eralib.pip(5, 15, RING) and not eralib.pip(11, 15, RING) and not eralib.pip(5, 21, RING))

tmp = tempfile.mkdtemp(prefix="era-")

# ---------------------------------------------------------------- 2. erasnap.py
print("erasnap.py: reads the contract, and what it keeps, refuses and counts")
RULE = ("An era covers from <= year < to; a year equal to a boundary belongs to the newer era. Look in `regions` first, fall back to "
        "`countries` by slug, and stay silent where `quality` lists a gap or an overlap. null in `contested` or `approx` means nobody has assessed it.")


def ce(region, frm, to, regime="kingdom", label="Kingdom of Ruritania", approx=False, contested=False, basis="not-recorded", polity=None, **kw):
    e = {"id": "%s--era-%s" % (region, frm), "from": frm, "to": to, "present": to is None, "regime": regime, "regimeLabel": label, "polity": polity,
         "filedUnder": [], "basis": basis, "contested": contested, "approx": approx, "url": "/region/%s/#era-%s" % (region, frm)}
    e.update(kw)
    return e


CONTRACT = {
    "contract": {"name": "recordatlas-context", "version": "1.8.0", "documented": "/data/#context", "changes": []},
    "licence": "x", "generatedBy": "test", "generated": "2026-01-01", "rule": RULE, "counts": {},
    "regions": [
        {"id": "ruritania", "label": "Ruritania", "alt": [], "countries": ["RU"], "url": "/region/ruritania/", "eras": [
            ce("ruritania", 1000, 1700, regime="feudal", label="Dukes and Counts"),                       # shorthand regime: refused
            ce("ruritania", 1700, 1800, why="A placeholder lower bound, said so."),                       # kept
            ce("ruritania", 1800, 1850, approx=True),                                                     # marked approximate: refused
            ce("ruritania", 1850, "c. 1900", regime="republic", label="Republic of Ruritania"),           # words-only end: refused
            ce("ruritania", 1900, 1910, regime="nameless", label=""),                                     # no label: refused
            ce("ruritania", 1910, 1905),                                                                  # start not before end: refused
            ce("ruritania", 1910, 1920, regime="brief", label="The Short Republic"),                      # kept
            ce("ruritania", 1920, 1950, regime="brief", label="The Short Republic"),                      # outside `existed`: refused
            ce("ruritania", 1950, 1990, regime="napo", label="Napoleonic", polity="Napoleonic — Fake Provinces"),   # qualified: kept
            ce("ruritania", 1980, 2000, regime="republic", label="Republic of Ruritania"),                # overlaps the one before: both contested
            ce("ruritania", 2000, None, regime="republic", label="Republic of Ruritania"),                # running: kept
        ]},
        {"id": "elphberg", "label": "Elphberg", "alt": [], "countries": [], "url": "/region/elphberg/", "eras": [
            ce("elphberg", 1700, 1800, basis="seeded:test-archive"),
            ce("elphberg", 1800, 1900, regime="napo", label="Napoleonic", polity=None, basis="seeded:test-archive"),           # shorthand, no polity: refused
            ce("elphberg", 1900, 1950, regime="napo", label="Napoleonic", polity="French Illyria", basis="seeded:test-archive"),  # "Napoleonic - French Illyria"
        ]},
        {"id": "unknownbasis", "label": "U", "alt": [], "countries": [], "url": "/region/unknownbasis/", "eras": [ce("unknownbasis", 1700, 1800, basis="unknown")]},
        {"id": "nullr", "label": "N", "alt": [], "countries": [], "url": "/region/nullr/", "eras": [
            ce("nullr", 1700, 1800, approx=None, contested=None), ce("nullr", 1800, 1900, approx=False, contested=None),
            ce("nullr", 1900, 2000, approx=None, contested=False)]},
        {"id": "gapped", "label": "G", "alt": [], "countries": [], "url": "/region/gapped/", "eras": [
            ce("gapped", 1700, 1800), ce("gapped", 1800, 1900), ce("gapped", 1900, 2000), ce("gapped", 2000, 2100), ce("gapped", 2100, 2200)]},
        {"id": "badids", "label": "B", "alt": [], "countries": [], "url": "/region/badids/", "eras": [
            ce("badids", 1700, 1800, id="badids--era-1701"), ce("badids", 1800, 1900, url="/region/other/#era-1800"), ce("badids", 1900, None, present=False)]},
        {"id": "unused", "label": "U", "alt": [], "countries": [], "url": "/region/unused/", "eras": [ce("unused", 1700, 1800)]},
        {"id": "eastland", "label": "E", "alt": [], "countries": [], "url": "/region/eastland/", "eras": [
            ce("eastland", 1700, 1750), ce("eastland", 1750, 1800, regime="eastern", label="Eastern Republic")]},
    ],
    "countries": [],
    "quality": {"gaps": [{"slug": "x-flags", "from": "x-flags--era-1", "to": "x-flags--era-2", "years": 3, "verdict": "unreviewed"},
                         {"slug": "gapped", "from": "gapped--era-1800", "to": "gapped--era-1900", "years": 1, "verdict": "unreviewed"}],
                "overlaps": [{"slug": "gapped", "from": "gapped--era-2000", "to": "gapped--era-2100", "years": 9, "verdict": "concurrent"},
                             {"slug": "y-flags", "from": "y-flags--era-1", "to": "y-flags--era-2", "years": 3, "verdict": "concurrent"}]},
}
RING_OF = {"ruritania": RING, "elphberg": [[20, 10], [20, 20], [30, 20], [30, 10]], "unknownbasis": [[40, 10], [40, 20], [50, 20], [50, 10]],
           "nullr": [[60, 10], [60, 20], [70, 20], [70, 10]], "gapped": [[-20, 10], [-20, 20], [-10, 20], [-10, 10]],
           "badids": [[-40, 10], [-40, 20], [-30, 20], [-30, 10]], "unused": [[-60, 10], [-60, 20], [-50, 20], [-50, 10]],
           "eastland": [[0, 20], [0, 30], [10, 30], [10, 20]]}
for r_ in CONTRACT["regions"]:                        # the contract (1.8.0) carries each region's ring and bbox
    r_["ring"] = RING_OF[r_["id"]]
    r_["bbox"] = [min(p_[0] for p_ in r_["ring"]), min(p_[1] for p_ in r_["ring"]), max(p_[0] for p_ in r_["ring"]), max(p_[1] for p_ in r_["ring"])]
RINGS = {"regimes": {"brief": {"label": "The Short Republic", "existed": [1910, 1920]}, "kingdom": {"label": "Kingdom of Ruritania"}},
         "regions": [
             {"id": "ruritania", "ring": RING, "eras": CONTRACT["regions"][0]["eras"]},
             {"id": "elphberg", "ring": [[20, 10], [20, 20], [30, 20], [30, 10]], "eras": CONTRACT["regions"][1]["eras"]},
             {"id": "unknownbasis", "ring": [[40, 10], [40, 20], [50, 20], [50, 10]], "eras": CONTRACT["regions"][2]["eras"]},
             {"id": "nullr", "ring": [[60, 10], [60, 20], [70, 20], [70, 10]], "eras": CONTRACT["regions"][3]["eras"]},
             {"id": "gapped", "ring": [[-20, 10], [-20, 20], [-10, 20], [-10, 10]], "eras": CONTRACT["regions"][4]["eras"]},
             {"id": "badids", "ring": [[-40, 10], [-40, 20], [-30, 20], [-30, 10]], "eras": CONTRACT["regions"][5]["eras"]},
             {"id": "unused", "ring": [[-60, 10], [-60, 20], [-50, 20], [-50, 10]], "eras": CONTRACT["regions"][6]["eras"]},
             {"id": "eastland", "ring": RING_OF["eastland"], "eras": CONTRACT["regions"][7]["eras"]},
         ]}
cp = os.path.join(tmp, "context.json")
open(cp, "w").write(json.dumps(CONTRACT))
rp = os.path.join(tmp, "rings.json")
json.dump(RINGS, open(rp, "w"))
TABLE = {"places": {
    "Centre": {"region": "ruritania", "lat": 5, "lon": 15}, "CENTRE!": "ruritania",
    "Near South": {"region": "ruritania", "lat": 0.1, "lon": 15}, "Near South Outside": {"region": "ruritania", "lat": -0.1, "lon": 15},
    "Far Outside": {"region": "ruritania", "lat": 80, "lon": 80}, "Wrong Ring": {"region": "ruritania", "lat": 25, "lon": 15},
    "Marked": {"region": "ruritania", "lat": 5, "lon": 15, "edge": True}, "No Coords": "elphberg", "Unk": {"region": "unknownbasis", "lat": 45, "lon": 15},
    "Nul": {"region": "nullr", "lat": 65, "lon": 15}, "Gap": {"region": "gapped", "lat": -15, "lon": 15}, "Bad": {"region": "badids", "lat": -35, "lon": 15},
    "Near East": {"region": "ruritania", "lat": 5, "lon": 19.9}, "Nowhere": None, "Dash": "-"}}
tp = os.path.join(tmp, "places.json")
json.dump(TABLE, open(tp, "w"))
out = os.path.join(tmp, "snap.json")
base = ["--contract", cp, "--places", tp, "--out", out, "--built", "2026-01-02"]           # the rings come from the contract
base_file = ["--contract", cp, "--rings", rp, "--places", tp, "--out", out, "--built", "2026-01-02"]   # ... or from an override file
rep = os.path.join(tmp, "report.json")
c, o = run("erasnap.py", base + ["--unassessed", "allow", "--report", rep])
snap = json.load(open(out)) if c == 0 else {}
case("it builds a version 3 snapshot from the contract (its rings and bboxes) and an archive's place table", c == 0 and snap.get("version") == 3, o)
want_sha = hashlib.sha256(open(cp, "rb").read()).hexdigest()
case("it records the contract's version, its generated stamp and the sha256 of the file's bytes",
     snap.get("contract") == {"name": "recordatlas-context", "version": "1.8.0", "generated": "2026-01-01", "sha256": want_sha}, snap.get("contract"))
case("it records where the rings came from: the contract (no second file, so no second hash)", snap.get("atlas") == {"base": "https://recordatlas.org", "rings_source": "contract", "rings_sha256": None}, snap.get("atlas"))
case("it records its policy: unassessed, boundary (from the contract's rule), quiet-rule year, edge km",
     snap.get("policy") == {"unassessed": "allow", "boundary": "newer", "recent_from": 1990, "edge_km": 15.0, "edge": "agree"}, snap.get("policy"))
case("only the regions the archive's table uses (and the neighbours of its edge places) are kept", sorted(snap.get("regions", {})) == ["badids", "eastland", "elphberg", "gapped", "nullr", "ruritania", "unknownbasis"], list(snap.get("regions", {})))
R = snap.get("regions", {}).get("ruritania", [])
case("the kept eras of a region carry the contract's id, its url, its label and its basis",
     [(e["id"], e["from"], e["to"], e["present"]) for e in R] == [("ruritania--era-1700", 1700, 1800, False), ("ruritania--era-1910", 1910, 1920, False),
                                                                  ("ruritania--era-1920", 1920, 1950, False), ("ruritania--era-1950", 1950, 1990, False), ("ruritania--era-1980", 1980, 2000, False),
                                                                  ("ruritania--era-2000", 2000, None, True)], R)
case("an open end is kept only for an era marked present, and carries to null", R and R[-1]["to"] is None and R[-1]["present"] is True)
case("each kept era carries assessed (neither flag null) and the contract's why (text, or null)",
     R[0]["assessed"] is True and R[0]["why"] == "A placeholder lower bound, said so." and all(e["why"] is None for e in R[1:])
     and [e["assessed"] for e in snap["regions"]["nullr"]] == [False, False, False], [(e["assessed"], e["why"]) for e in R])
dr = [(d["region"], d["from"], d["reason"].split()[0]) for d in snap.get("dropped", []) if d["region"] == "ruritania"]
case("a shorthand regime, a marked-approximate era, a words-only end, an empty label and an inverted span are all refused (5)",
     sorted(dr) == sorted([("ruritania", 1000, "regime"), ("ruritania", 1800, "marked"), ("ruritania", 1850, "end"), ("ruritania", 1900, "regime"),
                           ("ruritania", 1910, "start")]), dr)
cf, of = run("erasnap.py", base_file[:-4] + ["--out", os.path.join(tmp, "snap_file.json"), "--built", "2026-01-02", "--unassessed", "allow"])
sf = json.load(open(os.path.join(tmp, "snap_file.json"))) if cf == 0 else {}
case("with --rings <file> as an OVERRIDE: the source is recorded as the file and its hash, and the era outside the dates the Atlas holds for its regime is refused too",
     cf == 0 and sf["atlas"] == {"base": "https://recordatlas.org", "rings_source": "file", "rings_sha256": hashlib.sha256(open(rp, "rb").read()).hexdigest()}
     and any(d["region"] == "ruritania" and d["from"] == 1920 and d["reason"].startswith("era outside") for d in sf["dropped"])
     and sf["places"] == snap["places"] and sf["edge_neighbours"] == snap["edge_neighbours"] and sf["places_silent"] == snap["places_silent"], of)
case("a bare shorthand regime is shown with its polity (never invented); one with no polity is refused",
     [e["label"] for e in R if e["from"] == 1950] == ["Napoleonic — Fake Provinces"]
     and [e["label"] for e in snap["regions"]["elphberg"]] == ["Kingdom of Ruritania", "Napoleonic — French Illyria"]
     and any(d["region"] == "elphberg" and d["from"] == 1800 and d["reason"].startswith("bare shorthand") for d in snap["dropped"]), snap["regions"]["elphberg"])
case("two overlapping eras are both kept and both flagged contested", [e["contested"] for e in R if e["from"] in (1950, 1980)] == [True, True], R)
case("an era's contested/approx null is carried as null when the policy allows it", [(e["approx"], e["contested"]) for e in snap["regions"]["nullr"]] == [(None, None), (False, None), (None, False)])
case("basis is carried, and seeded_from_archive follows it (only a basis that starts 'seeded:')",
     all(e["seeded_from_archive"] for e in snap["regions"]["elphberg"]) and not any(e["seeded_from_archive"] for e in R)
     and snap["regions"]["unknownbasis"][0]["basis"] == "unknown" and snap["regions"]["unknownbasis"][0]["seeded_from_archive"] is False)
gp = snap["dropped"]
case("an era the contract's quality block lists in a gap or an overlap is refused, with its own reason",
     sorted((d["from"], d["reason"].split()[-1]) for d in gp if d["region"] == "gapped") == [(1800, "gaps"), (1900, "gaps"), (2000, "overlaps"), (2100, "overlaps")]
     and [e["from"] for e in snap["regions"]["gapped"]] == [1700], [(d["from"], d["reason"]) for d in gp if d["region"] == "gapped"])
case("an id or a url that is not the one the region and start imply, and an open end not marked present, are refused",
     sorted(d["from"] for d in gp if d["region"] == "badids") == [1700, 1800, 1900] and snap["regions"]["badids"] == [])
case("the contract's quality entries that name a region of the snapshot are carried, with the contract's own counts",
     snap["quality"]["counts"] == {"gaps": 2, "overlaps": 2} and [r["slug"] for r in snap["quality"]["gaps"]] == ["gapped"] and [r["slug"] for r in snap["quality"]["overlaps"]] == ["gapped"], snap["quality"])
pk, ps = snap.get("places", {}), snap.get("places_silent", {})
case("two spellings of one place are one key; a null or dash region is not a place", "centre" in pk and "nowhere" not in pk and "dash" not in pk and "nowhere" not in ps)
case("a place within 15 km of its region's ring edge (inside or outside it) with NO neighbouring region to compare is refused as 'edge'",
     ps.get("near south") == "edge" and ps.get("near south outside") == "edge", ps)
en = snap.get("edge_neighbours", {})
case("a place within 15 km of its region's edge with a neighbour whose ring lies within 15 km is kept, with that neighbour recorded",
     "near east" in pk and en.get("near east") == {"kind": "edge", "regions": ["eastland"]} and "near east" not in ps, (en, ps))
case("a place inside another region's ring and not its own is kept as a 'ring-conflict', with the region whose ring holds it",
     "wrong ring" in pk and en.get("wrong ring") == {"kind": "ring-conflict", "regions": ["elphberg"]} and "wrong ring" not in ps, (en, ps))
case("an ordinary place has no neighbours recorded", "centre" in pk and "centre" not in en and "far outside" not in en and "no coords" not in en, en)
case("a place the archive's table marks edge is refused as 'marked-edge'", ps.get("marked") == "marked-edge", ps)
case("a place far outside its own ring and near no other is kept and counted", "far outside" in pk and any(
     l.split()[:2] == ["places_outside_own_ring_kept", "1"] for l in o.splitlines()), o)
case("a place with no coordinates is kept, and listed unchecked (not edge-checked); a spelling of another place that has them checks it", "no coords" in pk and snap.get("unchecked_edge") == ["no coords"], snap.get("unchecked_edge"))
case("what it built answers as the library does: boundary, running era, edge, unchecked, unassessed",
     (eralib.era_at(snap, "Centre", 1750) or {}).get("id") == "ruritania--era-1700"
     and (eralib.era_at(snap, "Centre", 1910) or {}).get("boundary") is True                      # 1910 follows ... the refused 1900 era ends 1910
     and eralib.why_not(snap, "Centre", 2010) == "recent" and eralib.why_not(snap, "Near South", 1750) == "edge"
     and (eralib.era_at(snap, "No Coords", 1750) or {}).get("unchecked") is True and (eralib.era_at(snap, "Nul", 1750) or {}).get("unassessed") is True
     and eralib.why_not(snap, "Centre", 1985) == "contested" and eralib.why_not(snap, "Centre", 1995) == "contested")
ne = lambda y: eralib.era_at(snap, "Near East", y)
case("...and an edge place: noted where its neighbour has the same label, silent where it differs or has no era (the library reads edge_neighbours)",
     (ne(1720) or {}).get("edgeAgree") is True and (ne(1720) or {}).get("assessed") is True and eralib.why_not(snap, "Near East", 1760) == "edge"
     and eralib.why_not(snap, "Near East", 1912) == "edge" and (eralib.era_at(snap, "Wrong Ring", 1720) or {}).get("edgeAgree") is True
     and eralib.why_not(snap, "Wrong Ring", 1912) == "ring-conflict", [eralib.why_not(snap, "Near East", y) for y in (1720, 1760, 1912)])
case("the output tells the counts and names no place", "places_refused_edge" in o and "Centre" not in o and "Near South" not in o, o)
r = json.load(open(rep))
case("--report gives, per region, the eras refused and why (all regions, counts only)",
     r["eras_dropped_by_region"]["ruritania"] and "unused" in r["eras_in_by_region"] and r["eras_in"] == sum(len(x["eras"]) for x in CONTRACT["regions"]) and "Centre" not in json.dumps(r), r.get("eras_in"))

# the default policy: unassessed eras are refused
c1, o1 = run("erasnap.py", base[:-2] + ["--out", os.path.join(tmp, "snap_refuse.json"), "--built", "2026-01-02"])
sr = json.load(open(os.path.join(tmp, "snap_refuse.json"))) if c1 == 0 else {}
case("by default an era whose contested or approx is null is REFUSED (nobody assessed it), with a counted reason",
     c1 == 0 and sr["policy"]["unassessed"] == "refuse" and sr["regions"]["nullr"] == []
     and sorted(d["reason"] for d in sr["dropped"] if d["region"] == "nullr") == ["contested or approx not assessed (null)"] * 3
     and "contested or approx not assessed (null)" in o1, o1)
case("...and an assessed era (false, false) is kept under that default", [e["from"] for e in sr["regions"]["ruritania"]] == [1700, 1910, 1920, 1950, 1980, 2000], sr.get("regions", {}).get("ruritania"))
case("...so the library gives no note for a null-flag era under the default", eralib.why_not(sr, "Nul", 1750) in ("era-refused", "no-era"))

c2, o2 = run("erasnap.py", base + ["--unassessed", "allow", "--check"])
case("--check passes on a snapshot rebuilt from the same inputs", c2 == 0, o2)
s2 = json.load(open(out))
s2["regions"]["ruritania"][0]["label"] = "Edited by hand"
json.dump(s2, open(out, "w"))
c2, o2 = run("erasnap.py", base + ["--unassessed", "allow", "--check"])
case("--check fails on a snapshot edited by hand", c2 == 1, o2)
json.dump(snap, open(out, "w"))

c3, o3 = run("erasnap.py", base[:-2] + ["--out", os.path.join(tmp, "x.json"), "--unassessed", "allow", "--recent-from", "1950", "--edge-km", "30"])
s3 = json.load(open(os.path.join(tmp, "x.json"))) if c3 == 0 else {}
case("--recent-from and --edge-km are recorded in the policy, and --edge-km moves the rule",
     s3.get("policy", {}).get("recent_from") == 1950 and s3["policy"]["edge_km"] == 30.0, s3.get("policy"))
c3, o3 = run("erasnap.py", base[:-2] + ["--out", os.path.join(tmp, "x.json"), "--unassessed", "allow", "--outside-ring", "refuse"])
s3 = json.load(open(os.path.join(tmp, "x.json"))) if c3 == 0 else {}
case("--outside-ring refuse silences a place whose coordinates are outside its own ring", "far outside" not in s3.get("places", {}) and "far outside" in s3.get("places_silent", {}))

# the contract's own words are read, not assumed
def mutate_contract(fn, name):
    d = copy.deepcopy(CONTRACT)
    fn(d)
    p = os.path.join(tmp, name)
    json.dump(d, open(p, "w"))
    return p

p = mutate_contract(lambda d: d["contract"].update(version="2.0.0"), "c2.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--rings", rp, "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("a contract of another MAJOR version is refused (exit 2): a renamed field is what a major version is for", c4 == 2 and "major version 1" in o4, o4)
p = mutate_contract(lambda d: d["contract"].update(version="1.9.3"), "c19.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--rings", rp, "--places", tp, "--out", os.path.join(tmp, "y.json"), "--unassessed", "allow"])
case("a later minor version of major 1 is read, and recorded", c4 == 0 and json.load(open(os.path.join(tmp, "y.json")))["contract"]["version"] == "1.9.3", o4)
p = mutate_contract(lambda d: d["contract"].update(name="something-else"), "cn.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--rings", rp, "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("a file that is not the Atlas's contract is refused", c4 != 0, o4)
p = mutate_contract(lambda d: d.update(rule="An era covers its years."), "cr.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--rings", rp, "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("a contract whose rule does not state the half-open interval is refused (exit 2)", c4 == 2, o4)
p = mutate_contract(lambda d: d.update(rule="An era covers from <= year < to. Stay silent at a boundary."), "cs.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--rings", rp, "--places", tp, "--out", os.path.join(tmp, "y.json"), "--unassessed", "allow"])
case("a rule that does not say a boundary year belongs to the newer era gives boundary 'silent' (so boundary years stay silent)",
     c4 == 0 and json.load(open(os.path.join(tmp, "y.json")))["policy"]["boundary"] == "silent", o4)
c4, o4 = run("erasnap.py", ["--contract", p, "--rings", rp, "--places", tp, "--out", os.path.join(tmp, "y.json"), "--boundary", "newer"])
case("--boundary newer is refused where the contract does not say so (stricter is allowed, looser is not)", c4 != 0, o4)
c4, o4 = run("erasnap.py", base[:-2] + ["--out", os.path.join(tmp, "y.json"), "--boundary", "silent", "--unassessed", "allow"])
case("--boundary silent makes a contract that says 'newer' stricter", c4 == 0 and json.load(open(os.path.join(tmp, "y.json")))["policy"]["boundary"] == "silent", o4)
RR = copy.deepcopy(RINGS)
RR["regions"] = RR["regions"][:-1]
rp2 = os.path.join(tmp, "rings2.json")
json.dump(RR, open(rp2, "w"))
c4, o4 = run("erasnap.py", ["--contract", cp, "--rings", rp2, "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("a ring file that describes other regions than the contract is refused (exit 2)", c4 == 2, o4)
RR = copy.deepcopy(RINGS)
RR["regions"][0] = dict(RR["regions"][0], eras=RR["regions"][0]["eras"][:-1])
json.dump(RR, open(rp2, "w"))
c4, o4 = run("erasnap.py", ["--contract", cp, "--rings", rp2, "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("a ring file whose eras differ from the contract's is refused (exit 2)", c4 == 2, o4)
c4, o4 = run("erasnap.py", ["--contract", cp, "--rings", rp, "--no-rings", "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("--rings and --no-rings together contradict each other (exit 2)", c4 == 2, o4)
p = mutate_contract(lambda d: d["contract"].update(version="1.7.0"), "c17.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("a contract older than 1.8.0 carries no rings, and with neither --rings nor --no-rings it is refused (exit 2): not checking must be said", c4 == 2 and "carries no rings" in o4, o4)
c4, o4 = run("erasnap.py", ["--contract", p, "--rings", rp, "--places", tp, "--out", os.path.join(tmp, "y.json"), "--unassessed", "allow"])
case("...and with the override file it is read, the file being the source", c4 == 0 and json.load(open(os.path.join(tmp, "y.json")))["atlas"]["rings_source"] == "file", o4)
p = mutate_contract(lambda d: d["regions"][0].update(bbox=[0, 0, 1, 1]), "cbb.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--places", tp, "--out", os.path.join(tmp, "y.json")])
case("a bbox that is not its ring's extent stops the build: the contract contradicts itself (exit 2)", c4 == 2 and "extent" in o4, o4)
p = mutate_contract(lambda d: d["regions"][7].pop("ring"), "cnr.json")
c4, o4 = run("erasnap.py", ["--contract", p, "--places", tp, "--out", os.path.join(tmp, "y.json"), "--unassessed", "allow"])
sy = json.load(open(os.path.join(tmp, "y.json"))) if c4 == 0 else {}
case("a region with no ring at all means the neighbours cannot be known: every near-edge place is refused as before, and the count is told",
     c4 == 0 and sy["places_silent"].get("near east") == "edge" and sy["places_silent"].get("wrong ring") == "ring-conflict" and sy["edge_neighbours"] == {}
     and "regions_without_a_usable_ring" in o4, o4)
cS, oS = run("erasnap.py", base[:-2] + ["--out", os.path.join(tmp, "y.json"), "--unassessed", "allow", "--edge", "strict"])
sy = json.load(open(os.path.join(tmp, "y.json"))) if cS == 0 else {}
case("--edge strict is the old rule: every near-edge place and every ring conflict is refused, none kept with neighbours, and the policy says so",
     cS == 0 and sy["policy"]["edge"] == "strict" and sy["edge_neighbours"] == {} and sy["places_silent"].get("near east") == "edge"
     and sy["places_silent"].get("wrong ring") == "ring-conflict" and "near south" in sy["places_silent"], oS)
c4, o4 = run("erasnap.py", ["--contract", cp, "--no-rings", "--places", tp, "--out", os.path.join(tmp, "y.json"), "--unassessed", "allow"])
sn = json.load(open(os.path.join(tmp, "y.json"))) if c4 == 0 else {}
case("--no-rings keeps every mapped place and lists every one as not edge-checked", c4 == 0 and sn["places_silent"] == {"marked": "marked-edge"} and len(sn["unchecked_edge"]) == len(sn["places"]), o4)
json.dump({"places": {"Hentzau": "narnia"}}, open(tp, "w"))
c2, o2 = run("erasnap.py", base)
case("a place sent to a region the contract does not hold stops the build", c2 != 0 and "narnia" in o2, o2)
json.dump({"places": {"Hentzau": "ruritania", "hentzau": "elphberg"}}, open(tp, "w"))
c2, o2 = run("erasnap.py", base)
case("two spellings of one place sent to two regions stop the build", c2 != 0, o2)
json.dump({"places": {"Centre": {"region": "ruritania", "lat": 5, "lon": 15}, "centre": {"region": "ruritania", "lat": 0.1, "lon": 15}}}, open(tp, "w"))
c2, o2 = run("erasnap.py", base + ["--unassessed", "allow"])
s5 = json.load(open(out))
case("two spellings of one place, one of them on the edge: the refusal wins", c2 == 0 and s5["places"] == {} and s5["places_silent"] == {"centre": "edge"}, s5.get("places_silent"))
json.dump(TABLE, open(tp, "w"))
json.dump(snap, open(out, "w"))

# ---------------------------------------------------------------- 3. checkera.py
print("checkera.py: a planted fault for each rule")
CLEAN = CASES["gate_snapshot"]
ERA_URL = "https://atlas.example.test/region/%s/#era-%s"


def note(id_="ruritania--era-1700", year="1750", label="Kingdom of Ruritania", src="per the Record Atlas", href=ERA_URL % ("ruritania", 1700), boundary=False,
         pre=None, assessed="1", edge=False):
    a = '<a class="era-src" href="%s" rel="noopener">%s</a>' % (href, src) if href else '<span class="era-src">%s</span>' % src
    b = ' data-era-boundary="1"' if boundary else ""
    m = (' data-era-assessed="%s"' % assessed if assessed is not None else "") + (' data-era-edge-agree="1"' if edge else "")
    pre = pre if pre is not None else ("· From that year: " if boundary else "· At the time: ")
    return ('<span class="era-note" data-era="%s" data-era-year="%s"%s%s><span class="era-pre">%s</span>'
            '<span class="era-lab">%s</span> %s</span>' % (id_, year, b, m, pre, label, a))


ERA_CSS = '<style is:inline data-era-css>.era-note{display:block;color:var(--ink-2,#444)}</style>'


def page(body, head="", attrs="", css=True):
    """A page as the component draws it: the era style once, ahead of the first note, and none on a page with no note."""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>A page</title>%s</head><body %s><main><h1>A person</h1>'
            '<div class="v">Hentzau%s%s</div></main></body></html>' % (head, attrs, ERA_CSS if (css and "era-note" in body) else "", body))


def unassess(s, region="ruritania", i=0, **flags):
    """An era the Atlas has not assessed, as the snapshot would carry it (the stored assessed flag follows the two flags)."""
    e = s["regions"][region][i]
    e.update(flags or {"contested": None})
    e["assessed"] = e["approx"] is not None and e["contested"] is not None
    return s


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
case("...and the summary says which contract, and what policy, the snapshot rests on", "contract 1.7.0 of 2026-01-01" in o and "unassessed refuse" in o and "recent from 1990" in o, o)
c, o = gate({P: page(note()), "people/b/index.html": page(note("elphberg--era-1900", "1975", "Kingdom of Ruritania", "per this archive's own research",
                                                                ERA_URL % ("elphberg", 1900)))})
case("control: a note on a seeded era that says so passes, and is counted as seeded", c == 0 and "1 on a seeded region" in o, o)
c, o = gate({P: page(note("ruritania--era-1850", "1850", "Republic of Ruritania", href=ERA_URL % ("ruritania", 1850), boundary=True))})
case("control: a boundary-year note, marked and worded as one, passes and is counted", c == 0 and "1 on a boundary year" in o, o)


def fails(label, pages, cat, snap=CLEAN, extra=None, code=1, snap_text=None):
    c, o = gate(pages, snap, extra, snap_text)
    case(label, c == code and (cat is None or cat in o), "exit %s: %s" % (c, o))


print("  rule a/b: a note must name an era of the contract the snapshot holds")
fails("an id that is not an era the snapshot holds", {P: page(note("ruritania--era-1701"))}, "unknown 1")
fails("a region the snapshot lacks", {P: page(note("narnia--era-1700"))}, "unknown 1")
fails("the old id shape region--year is not the contract's id", {P: page(note("ruritania--1700"))}, "unknown 1")
fails("a data-era with no shape at all", {P: page(note("ruritania"))}, "unknown 1")
fails("an era the snapshot flags approximate", {P: page(note("ruritania--era-1800", "1820", "Occupied Ruritania", href=ERA_URL % ("ruritania", 1800)))}, "ineligible 1")
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["contested"] = True
fails("an era the snapshot flags contested", {P: page(note())}, "ineligible 1", s)
s = unassess(copy.deepcopy(CLEAN))
fails("an era the Atlas has not assessed (null) under the refuse policy", {P: page(note())}, "ineligible 1", s)
s = copy.deepcopy(s); s["policy"]["unassessed"] = "allow"
fails("...but not under the allow policy: it passes if it says so (data-era-assessed 0), and the summary counts it", {P: page(note(assessed="0"))}, "0 on an era the Atlas has assessed, 1 on one it has not", s, code=0)
fails("...a note on that era that says it rests on an assessed era fails (assessed)", {P: page(note())}, "assessed 1", s)
fails("...and --strict-unassessed refuses that policy", {P: page(note(assessed="0"))}, "unassessed-policy 1", s, extra=["--strict-unassessed"])
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"].append(dict(s["regions"]["ruritania"][0], id="ruritania--era-1790", **{"from": 1790, "to": 1810, "url": "/region/ruritania/#era-1790"}))
fails("an era that overlaps another of its region", {P: page(note())}, "ineligible 1", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["label"] = "  "
fails("an era whose label is empty (the snapshot is refused as malformed first)", {P: page(note(label=""))}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["to"] = "c. 1800"
fails("an era with a words-only end (malformed snapshot)", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["elphberg"][0]["present"] = False
fails("an open end on an era not marked present (malformed snapshot)", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["id"] = "ruritania--era-1701"
fails("an era whose id is not its region and start (malformed snapshot)", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["url"] = "/region/elsewhere/#era-1700"
fails("an era whose url is not its own (malformed snapshot)", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["elphberg"][0]["seeded_from_archive"] = False
fails("a seeded basis whose flag says otherwise (malformed snapshot)", {P: page(note())}, "malformed", s)
print("  the year: from <= year < to")
fails("a year after the era", {P: page(note(year="1850"))}, "year 1")
fails("the year an era ENDS in (it belongs to the next)", {P: page(note(year="1800"))}, "year 1")
fails("a year before the era", {P: page(note(year="1650"))}, "year 1")
fails("no year on the note", {P: page(note().replace(' data-era-year="1750"', ""))}, "year 1")
fails("a year that is not a number", {P: page(note(year="about 1750"))}, "year 1")
c, o = gate({P: page(note(year="1700"))})
case("the first year of the first era is inside it (no boundary: nothing precedes it)", c == 0, o)
print("  the quiet rule")
fails("a note in the running era from the quiet-rule year", {P: page(note("elphberg--era-1900", "1990", "Kingdom of Ruritania", "per this archive's own research", ERA_URL % ("elphberg", 1900)))}, "recent 1")
c, o = gate({P: page(note("elphberg--era-1900", "1989", "Kingdom of Ruritania", "per this archive's own research", ERA_URL % ("elphberg", 1900)))})
case("the year before it is fine", c == 0, o)
s = copy.deepcopy(CLEAN); s["policy"]["recent_from"] = 2000
c, o = gate({P: page(note("elphberg--era-1900", "1995", "Kingdom of Ruritania", "per this archive's own research", ERA_URL % ("elphberg", 1900)))}, s)
case("the snapshot's own quiet-rule year is the one the gate holds the page to", c == 0, o)
print("  boundary years")
fails("a boundary-year note that is not marked as one", {P: page(note("ruritania--era-1850", "1850", "Republic of Ruritania", href=ERA_URL % ("ruritania", 1850)))}, "boundary 1")
fails("a boundary-year note marked, but worded 'at the time'", {P: page(note("ruritania--era-1850", "1850", "Republic of Ruritania", href=ERA_URL % ("ruritania", 1850), boundary=True, pre="· At the time: "))}, "boundary 1")
fails("an ordinary year marked as a boundary", {P: page(note(boundary=True))}, "boundary")
s = copy.deepcopy(CLEAN); s["policy"]["boundary"] = "silent"
fails("any boundary-year note when the snapshot's policy is not 'newer'", {P: page(note("ruritania--era-1850", "1850", "Republic of Ruritania", href=ERA_URL % ("ruritania", 1850), boundary=True))}, "boundary 1", s)
print("  words: the label and the source")
fails("a label that differs from the snapshot's label", {P: page(note(label="Empire of Ruritania"))}, "label 1")
fails("a note with no label", {P: page(note().replace('<span class="era-lab">Kingdom of Ruritania</span>', ""))}, "label 1")
fails("a note that does not say where it came from", {P: page(note(src="at the time"))}, "source 1")
fails("a seeded era's note that says 'per the Record Atlas' (rule f)", {P: page(note("elphberg--era-1900", "1975", "Kingdom of Ruritania", "per the Record Atlas", ERA_URL % ("elphberg", 1900)))}, "source 1")
fails("a link to the REGION, not the era (rule e)", {P: page(note(href="https://atlas.example.test/region/ruritania/"))}, "source 1")
fails("a link that is not the Atlas's", {P: page(note(href="https://elsewhere.example.test/"))}, "source 1")
fails("a source with no link at all", {P: page(note(href=None))}, "source 1")
print("  the era style: once on a page that has a note, nowhere else")
fails("a page with a note and no era style", {P: page(note(), css=False)}, "css 1")
fails("a page that draws the era style twice", {P: page(note() + ERA_CSS + note(year="1760"))}, "css 1")
fails("a page that carries the era style and no note (the weight the bundled component style put on every page)", {P: page(note()), "people/b/index.html": page("").replace("</main>", ERA_CSS + "</main>")}, "css 1")
fails("an era style without the note's rules in it", {P: page(note()).replace(".era-note{", ".x{")}, "css 1")
c, o = gate({P: page(note() + " " + note(year="1760") + " " + note(year="1770"))})
case("control: a page with three notes and one era style passes, and one page carries it", c == 0 and "3 note(s)" in o and "1 page(s) carry the era style, one each" in o, o)
c, o = gate({P: page(note()), "people/b/index.html": page("<p>no note here</p>")})
case("control: a page with no note carries no era style and passes", c == 0 and "2 page(s) read, 1 with a note" in o, o)
print("  assessed, and the edge mark")
fails("a note that says it rests on an unassessed era when the snapshot says assessed", {P: page(note(assessed="0"))}, "assessed 1")
fails("a note with no assessed mark", {P: page(note(assessed=None))}, "assessed 1")
fails("an assessed mark that is neither 1 nor 0", {P: page(note(assessed="yes"))}, "assessed 1")
fails("an edge-agree mark where the snapshot holds no edge place of the region", {P: page(note(edge=True))}, "edge 1")
s = copy.deepcopy(CLEAN); s["places"]["edgy"] = "ruritania"; s["edge_neighbours"]["edgy"] = {"kind": "edge", "regions": ["elphberg"]}
c, o = gate({P: page(note(edge=True))}, s)
case("control: an edge-agree mark where the snapshot holds such a place passes, and is counted", c == 0 and "1 at an edge where every neighbour agrees" in o and "(0 not edge-checked, 1 at an edge)" in o, o)
print("  rule c: no note on a living, held-out or noindex page")
fails("a note on a page that says noindex", {P: page(note(), '<meta name="robots" content="noindex, nofollow">')}, "noindex 1")
fails("a note on a page marked living", {P: page(note(), attrs='data-living="1"')}, "living 1")
print("  the gate must see something")
fails("no built site at all is not a pass (exit 2)", {}, "COULD NOT SEE A BUILT SITE", code=2)
fails("a site with pages and no note is not a pass (exit 2)", {P: page("")}, "FOUND 0 NOTE", code=2)
fails("an unreadable snapshot is not a pass (exit 2)", {P: page(note())}, "COULD NOT READ THE SNAPSHOT", code=2, snap_text="{ not json")
fails("a snapshot of another version is malformed", {P: page(note())}, "malformed", dict(CLEAN, version=1))
s = copy.deepcopy(CLEAN); s["contract"]["sha256"] = "abc"
fails("a snapshot that does not carry the contract's hash is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); del s["contract"]["version"]
fails("a snapshot that does not carry the contract's version is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["policy"]["unassessed"] = "maybe"
fails("a policy the gate does not understand is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["places"]["x"] = "narnia"
fails("a place sent to a region the snapshot lacks is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["places_silent"]["hentzau"] = "edge"
fails("a place both mapped and silent is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["places_silent"]["x"] = "banana"
fails("a silence reason the library does not know is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["unchecked_edge"] = ["nowhere"]
fails("an unchecked place that is not a mapped place is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); del s["atlas"]["rings_source"]
fails("a snapshot that does not say where its rings came from is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["atlas"]["rings_source"] = "file"
fails("...a ring file named without its hash is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); del s["policy"]["edge"]
fails("a policy without the edge rule is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["assessed"] = False
fails("an era whose assessed flag does not follow its contested and approx is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["why"] = 7
fails("an era whose why is not text or null is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["places"]["edgy"] = "ruritania"; s["edge_neighbours"]["edgy"] = {"kind": "edge", "regions": ["ruritania"]}
fails("an edge place whose neighbour is its own region is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["places"]["edgy"] = "ruritania"; s["edge_neighbours"]["edgy"] = {"kind": "edge", "regions": ["narnia"]}
fails("an edge place whose neighbour the snapshot does not hold is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["places"]["edgy"] = "ruritania"; s["edge_neighbours"]["edgy"] = {"kind": "banana", "regions": ["elphberg"]}
fails("an edge place of a kind the library does not know is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["edge_neighbours"]["ghost"] = {"kind": "edge", "regions": ["elphberg"]}
fails("an edge place that is not a mapped place is malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); s["policy"]["edge"] = "strict"; s["places"]["edgy"] = "ruritania"; s["edge_neighbours"]["edgy"] = {"kind": "edge", "regions": ["elphberg"]}
fails("edge neighbours under a strict edge policy are malformed", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); del s["edge_neighbours"]
fails("a snapshot with no edge_neighbours is malformed", {P: page(note())}, "malformed", s)
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
