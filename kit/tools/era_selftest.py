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
    for c in CASES["ruler_cases"]:
        s = copy.deepcopy(CASES["other_snapshots"][c["snap"]])
        try:
            got = lib.ruler_at(s, c["region"], c["year"])
            why = lib.why_no_ruler(s, c["region"], c["year"])
        except Exception as e:  # noqa: BLE001
            out.append(c["id"] + " (threw %s)" % type(e).__name__)
            continue
        if why != c["why"] or (c["name"] is None and got is not None) or (c["name"] is not None and (got is None or got["name"] != c["name"])):
            out.append(c["id"])
    for c in CASES["ruler_note_cases"]:
        s = copy.deepcopy(CASES["other_snapshots"][c["snap"]])
        try:
            got = lib.era_at(s, c["place"], c["year"])
        except Exception as e:  # noqa: BLE001
            out.append(c["id"] + " (threw %s)" % type(e).__name__)
            continue
        if (got is not None) != c["era"] or (c["era"] and ((got["ruler"] or {}).get("name") != c["ruler"] or got["boundary"] != c["boundary"])):
            out.append(c["id"])
    rs_ = copy.deepcopy(CASES["other_snapshots"]["rulers"])
    f_, q_ = lib.ruler_at(rs_, "rulerland", 1836), lib.ruler_at(rs_, "rulerland", 1745)
    if not (f_ and f_["polityId"] == "union-of-the-two-realms" and f_["from"] == "1830" and f_["to"] == "1859" and f_["fromYear"] == 1830 and f_["toYear"] == 1859
            and f_["q"] is None and q_ and q_["q"] == "Q1"):
        out.append("ruler:fields")
    if (lib.era_at(rs_, "Rulertown", 1745) or {}).get("place") != "rulertown":
        out.append("note:place")
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
    ("an approximate era is noted under the refuse policy", 'if ap == "yes" and pol.get("approx") != "margin":\n        return "approx"', "", "margin-approx-refuse-policy-refuses-an-approx-era"),
    ("an approximate era with no margin gets a note", 'if (ap == "yes" or co == "yes") and not (is_margin(e.get("from_margin")) and (is_open(e) or is_margin(e.get("to_margin")))):\n        return "approx" if ap == "yes" else "contested"',
     "", "margin-a-flagged-era-with-an-unknown-end-margin-is-silent"),
    ("a contested era is noted under the refuse policy", 'if cp not in ("scope", "margin"):\n            return "contested"', "", "margin-contested-refuse-policy-refuses-a-bounds-scope-era"),
    ("a regime scope on an unflagged era is used", 'sc = e.get("contested_scope")\n    if sc in ("regime", "part"):\n        return "contested"', 'sc = e.get("contested_scope")', "margin-a-regime-scope-on-an-era-that-is-not-flagged-contested-is-still-silent"),
    ("a contested era of an unknown scope is noted", 'if sc not in ("bounds", "none") and not', "if False and not", "margin-an-unknown-scope-on-a-contested-era-is-silent"),
    ("a contested era of scope none is refused", 'if sc not in ("bounds", "none") and not', 'if sc != "bounds" and not', "margin-a-contested-era-of-scope-none-is-used"),
    ("the floor is not applied", "max(n, m) + (n if soft else 0)", "m + (n if soft else 0)", "margin-margin-0-from-the-atlas-the-floor-still-holds-1805"),
    ("an unsourced margin is not softer", "max(n, m) + (n if soft else 0)", "max(n, m) + 0", "margin-an-unsourced-margin-of-2-1711-is-allowed-and-says-it-rests-on-an-unsourced-margin"),
    ("the snapshot's floor is ignored", 'pol["margin_years"] if isinstance(pol, dict) and is_margin(pol.get("margin_years")) else MARGIN_YEARS', "MARGIN_YEARS", "margin-margin-0-and-a-floor-of-0-is-a-clean-date-1800"),
    ("the unsourced mark is not carried on the era", '"unsourced": e.get("margin_sourced") is False and', '"unsourced": False and', "margin-an-unsourced-margin-of-2-1711-is-allowed-and-says-it-rests-on-an-unsourced-margin"),
    ("a contested era with no scope is noted under the scope policy", 'not (sc is None and cp == "margin")', "not (sc is None)", "margin-contested-with-no-scope-is-silent-under-the-scope-policy"),
    ("a contested era with no scope is never noted", 'not (sc is None and cp == "margin")', "True", "margin-contested-with-no-scope-is-allowed-10-years-inside-under-the-margin-policy"),
    ("the start margin is not applied", 'return None if year >= span["first"] and (span["last"] is None or year <= span["last"]) else "margin"',
     'return None if (span["last"] is None or year <= span["last"]) else "margin"', "margin-approx-1820-is-5-years-from-the-start-so-silent"),
    ("the end margin is not applied", 'return None if year >= span["first"] and (span["last"] is None or year <= span["last"]) else "margin"',
     'return None if year >= span["first"] else "margin"', "margin-approx-1856-is-5-years-from-the-end-so-silent"),
    ("a year AT the margin is allowed (at least, not more than)", '"first": e["from"] + (rf + 1 if rf is not None and rf > 0 else 0)', '"first": e["from"] + (rf if rf is not None else 0)', "margin-approx-1820-is-5-years-from-the-start-so-silent"),
    ("the end margin counts a year too few", '"last": None if is_open(e) else e["to"] - 1 - (rt if rt is not None else 0)', '"last": None if is_open(e) else e["to"] - (rt if rt is not None else 0)', "margin-approx-1856-is-5-years-from-the-end-so-silent"),
    ("a margin of 0 is silent in the first year", '"first": e["from"] + (rf + 1 if rf is not None and rf > 0 else 0)', '"first": e["from"] + (rf + 1 if rf is not None else 0)', "margin-margin-0-and-a-floor-of-0-is-a-clean-date-1800"),
    ("an unflagged era's own margin is ignored", "if not ap and not co and rf is None and rt is None:", "if not ap and not co:", "margin-an-unflagged-era-keeps-the-margin-the-contract-gives-it-1705"),
    ("the recorded decision is not held to the margins", 'if not isinstance(r, dict) or "last" not in r or r.get("kind") != span["kind"] or r.get("first") != span["first"] or r.get("last") != span["last"]:\n        return "bad-margin"',
     "", "margin-a-recorded-decision-that-does-not-follow-the-margins-is-silent"),
    ("a missing record is accepted", 'if not isinstance(r, dict) or "last" not in r or', 'if r is None:\n        return None\n    if not isinstance(r, dict) or "last" not in r or', "margin-a-flagged-era-with-no-recorded-decision-is-silent"),
    ("the approx mark is not carried on the era", '"approx": flag(e.get("approx")) == "yes",', '"approx": False,', "margin-approx-1830-in-1815-1861-keeps-its-note"),
    ("the contested mark is not carried on the era", '"contested": flag(e.get("contested")) == "yes",\n', '"contested": False,\n', "margin-contested-bounds-1822-is-allowed-under-scope-bounds"),
    ("an era that overlaps another is not contested", "any(any(o is not e and numeric(o) and meets(e, o) for o in eras) for e in covering)", "False", "an-era-that-overlaps-another-is-silent-even-where-it-stands-alone"),
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
    ("a snapshot of another version is read", 'snap.get("version") != VERSION:\n        return no("snapshot")\n    if not is_year(year):\n        return no("year")\n    if not isinstance(place',
     'False:\n        return no("snapshot")\n    if not is_year(year):\n        return no("year")\n    if not isinstance(place', "a-snapshot-of-the-first-version-is-refused"),
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
    ("a neighbour era that overlaps another elsewhere is trusted", "if any(o is not x and numeric(o) and meets(x, o) for o in eras):\n        return False\n    if margin_gate(",
     "if margin_gate(", "a-neighbour-era-that-overlaps-another-anywhere-is-silent"),
    ("a neighbour era marked approximate is trusted", 'if margin_gate(x, year, pol) is not None:\n        return False', 'if flag(x.get("contested")) == "yes" and margin_gate(x, year, pol) is not None:\n        return False',
     "a-place-near-an-edge-is-silent-where-its-neighbour-era-is-approximate"),
    ("a neighbour era marked contested is trusted", 'if margin_gate(x, year, pol) is not None:\n        return False', 'if flag(x.get("approx")) == "yes" and margin_gate(x, year, pol) is not None:\n        return False',
     "a-neighbour-marked-contested-is-silent"),
    ("a neighbour era's margins are ignored", 'if margin_gate(x, year, pol) is not None:\n        return False', 'if flag(x.get("approx")) == "yes" or flag(x.get("contested")) == "yes":\n        return False',
     "margin-an-edge-place-keeps-its-note-where-the-neighbour-is-approx-but-well-inside-it"),
    ("a neighbour era within its margin is trusted", 'if margin_gate(x, year, pol) is not None:\n        return False', "",
     "margin-an-edge-place-is-silent-where-the-neighbours-approx-era-is-within-its-margin"),
    ("a neighbour era contested about its regime is trusted", 'if margin_gate(x, year, pol) is not None:\n        return False', 'if flag(x.get("approx")) == "yes" and margin_gate(x, year, pol) is not None:\n        return False',
     "margin-an-edge-place-is-silent-where-the-neighbours-era-is-contested-about-its-regime"),
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
    # rule m: rulers
    ("a region the contract says has no rulers is named a ruler", ' or rs.get("has") is not True', "", "ruler-a-region-the-contract-says-has-no-rulers-is-silent-though-reigns-are-listed"),
    ("overlapping reigns: the first is picked", 'if len(touching) > 1:\n        return no("overlap")', "", "ruler-two-overlapping-reigns-are-silent-whichever-polity"),
    ("a reign's start margin does not widen it", 'r["from_year"] - r["from_margin"] <= year', 'r["from_year"] <= year', "ruler-the-year-before-the-federation-has-two-reigns-through-its-start-margin"),
    ("a reign's end margin does not widen it", 'year <= r["to_year"] + (r["to_margin"] or 0)', 'year <= r["to_year"]', "ruler-an-end-margin-of-1-widens-a-reign-one-year-past-its-end"),
    ("an open reign is measured from an end it has not got", '(r["to_year"] is not None and not r["to_year"] - year > max(n, r["to_margin"]))', '(not r["to_year"] - year > max(n, r["to_margin"]))', "ruler-an-open-reign-is-named-with-no-end-to-measure-from"),
    ("the floor is not applied at a reign's start", 'year - r["from_year"] > max(n, r["from_margin"])', 'year - r["from_year"] > r["from_margin"]', "ruler-within-5-years-of-the-reign-start-is-silent"),
    ("the floor is not applied at a reign's end", 'r["to_year"] - year > max(n, r["to_margin"])', 'r["to_year"] - year > r["to_margin"]', "ruler-within-5-years-of-the-reign-end-is-silent"),
    ("a year AT the reach of the start is allowed (at least, not more than)", 'year - r["from_year"] > max(n, r["from_margin"])', 'year - r["from_year"] >= max(n, r["from_margin"])', "ruler-the-year-AT-the-reach-is-silent-not-more-than-5"),
    ("a year AT the reach of the end is allowed", 'r["to_year"] - year > max(n, r["to_margin"])', 'r["to_year"] - year >= max(n, r["to_margin"])', "ruler-the-union-ruler-5-years-before-the-end-is-silent"),
    ("the snapshot's floor is ignored for rulers", 'n = floor_of(pol)\n    if not year - r["from_year"]', 'n = MARGIN_YEARS\n    if not year - r["from_year"]', "ruler-with-the-floor-off-a-zero-margin-reign-is-named-up-to-the-year-before-its-end-1736"),
    ("a reign of another polity is named", 'if not isinstance(allowed, list) or r["polity_id"] not in allowed:\n        return no("polity")', "", "ruler-the-reign-of-another-polity-is-silent"),
    ("a regime the polity table does not list is allowed any polity", 'if not isinstance(allowed, list) or r["polity_id"] not in allowed:', 'if isinstance(allowed, list) and r["polity_id"] not in allowed:', "ruler-a-regime-the-polity-table-does-not-list-is-silent"),
    ("two eras over the year do not silence the ruler", 'if len(covering) != 1 or refused:\n        return no("no-era")', 'if len(covering) < 1 or refused:\n        return no("no-era")', "ruler-two-kept-eras-over-the-year-is-silent"),
    ("a refused era over the year does not silence the ruler", 'if len(covering) != 1 or refused:\n        return no("no-era")', 'if len(covering) != 1:\n        return no("no-era")', "ruler-a-refused-era-over-the-year-is-silent"),
    ("an unusable reign row is ignored", 'if not all(reign_ok(r) for r in rs["reigns"]):\n        return no("bad-rows")', "", "ruler-a-region-with-an-unusable-reign-row-is-silent-whole"),
    ("the Atlas's name is changed", 'return {"name": r["name"],', 'return {"name": r["name"].upper(),', "ruler-a-year-well-inside-one-reign-names-it"),
    ("the polityId is not returned", '"polityId": r["polity_id"],', '"polityId": None,', "ruler:fields"),
    ("a boundary-year note names a ruler", '"ruler": None if d["boundary"] or d["edge_agree"] else ruler_at(snap, region, year)}', '"ruler": None if d["edge_agree"] else ruler_at(snap, region, year)}', "note-a-boundary-year-note-names-no-ruler-though-a-reign-covers-it"),
    ("an edge note names a ruler", '"ruler": None if d["boundary"] or d["edge_agree"] else ruler_at(snap, region, year)}', '"ruler": None if d["boundary"] else ruler_at(snap, region, year)}', "note-an-edge-note-names-no-ruler"),
    ("the note carries no ruler", '"ruler": None if d["boundary"] or d["edge_agree"] else ruler_at(snap, region, year)}', '"ruler": None}', "note-a-ruler-well-inside-a-reign-is-on-the-note"),
    ("the place is not returned by era_at", '"place": d["key"],', '"place": None,', "note:place"),
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
        ruler_at = staticmethod(ns["ruler_at"])
        why_no_ruler = staticmethod(ns["why_no_ruler"])
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
base = ["--contract", cp, "--approx", "refuse", "--places", tp, "--out", out, "--built", "2026-01-02"]           # the rings come from the contract
base_file = ["--contract", cp, "--approx", "refuse", "--rings", rp, "--places", tp, "--out", out, "--built", "2026-01-02"]   # ... or from an override file
rep = os.path.join(tmp, "report.json")
c, o = run("erasnap.py", base + ["--unassessed", "allow", "--report", rep])
snap = json.load(open(out)) if c == 0 else {}
case("it builds a version 5 snapshot from the contract (its rings and bboxes) and an archive's place table", c == 0 and snap.get("version") == 5, o)
want_sha = hashlib.sha256(open(cp, "rb").read()).hexdigest()
case("it records the contract's version, its generated stamp and the sha256 of the file's bytes",
     snap.get("contract") == {"name": "recordatlas-context", "version": "1.8.0", "generated": "2026-01-01", "sha256": want_sha}, snap.get("contract"))
case("it records where the rings came from: the contract (no second file, so no second hash)", snap.get("atlas") == {"base": "https://recordatlas.org", "rings_source": "contract", "rings_sha256": None}, snap.get("atlas"))
case("it records its policy: unassessed, boundary (from the contract's rule), quiet-rule year, edge km",
     snap.get("policy") == {"unassessed": "allow", "boundary": "newer", "recent_from": 1990, "edge_km": 15.0, "edge": "agree",
                            "approx": "refuse", "contested": "scope", "margin_years": 5, "margins": {},
                            "ruler_polities": {"italy": ["kingdom-of-italy", "italian-republic"], "twosicilies": ["kingdom-of-the-two-sicilies"]}}, snap.get("policy"))
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
case("two overlapping eras are both kept; the library (not a flag the contract never set) keeps every year they touch silent", [e["contested"] for e in R if e["from"] in (1950, 1980)] == [False, False] and "eras_overlapping_another_kept_era" in o, R)
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

# ---------------------------------------------------------------- 2b. erasnap.py: rule l, the boundary margins
print("erasnap.py: approx and contested eras are kept with margins (rule l); a synthetic contract 1.10.0 exercises the margin fields the Atlas is adding")


def ring_at(lat):
    return [[lat, 10], [lat, 20], [lat + 10, 20], [lat + 10, 10]]


def mk_region(rid, lat, eras):
    r_ = {"id": rid, "label": rid, "alt": [], "countries": [], "url": "/region/%s/" % rid, "eras": eras, "ring": ring_at(lat)}
    r_["bbox"] = [lat, 10, lat + 10, 20]
    return r_


# the contract 1.9.0 shape: flags and a `why`, no margins and no scope
C19 = copy.deepcopy(CONTRACT)
C19["contract"]["version"] = "1.9.0"
C19["quality"] = {"gaps": [], "overlaps": []}
C19["regions"] = [
    mk_region("calabrio", 0, [ce("calabrio", 1815, 1861, regime="kingdom", label="Kingdom of the Two Realms", approx=True, why="The start is a lower bound."),
                              ce("calabrio", 1861, None, regime="union", label="Union of Ruritania", approx=True, why="Annexation took more than a year.")]),
    mk_region("scoped", 10, [ce("scoped", 1816, 1861, regime="kingdom", label="Realm of the Seven Seats", contested=True, why="Garibaldi 1860 or annexation 1861."),
                             ce("scoped", 1861, None, regime="union", label="Union of Ruritania")]),
    mk_region("flat", 20, [ce("flat", 1900, 1950, regime="city", label="Free City", contested=True, why="The regime itself is disputed."),
                           ce("flat", 1950, 2000, regime="zone", label="Partitioned Zone", contested=True, why="A part of it is disputed.")]),
    mk_region("feud", 30, [ce("feud", 1000, 1700, regime="feudal", label="Dukes and Counts", approx=True, why="We do not know."),
                           ce("feud", 1700, 1800, regime="kingdom", label="Kingdom of Feud", contested=True, why="Bounds disputed.")]),
    mk_region("plain", 40, [ce("plain", 1700, 1800, regime="kingdom", label="Kingdom of Plain"), ce("plain", 1800, 1900, regime="duchy", label="Duchy of Plain")]),
]
TABLE19 = {"places": {"Calabrio": "calabrio", "Scopetown": "scoped", "Flatville": "flat", "Feudton": "feud", "Plainton": "plain"}}


def contract_with(fn, name):
    d_ = copy.deepcopy(C19)
    fn(d_)
    p_ = os.path.join(tmp, name)
    json.dump(d_, open(p_, "w"))
    return p_


def build19(contract, name, args=(), table=TABLE19):
    tp_ = os.path.join(tmp, "t19.json")
    json.dump(table, open(tp_, "w"))
    o_ = os.path.join(tmp, name)
    c_, t_ = run("erasnap.py", ["--contract", contract, "--no-rings", "--places", tp_, "--out", o_, "--built", "2026-01-02"] + list(args))
    return c_, t_, (json.load(open(o_)) if c_ == 0 else {})


def era19(sn, region, frm):
    return next((e for e in sn.get("regions", {}).get(region, []) if e["from"] == frm), None)


def why19(sn, region, frm):
    return next((d["reason"] for d in sn.get("dropped", []) if d["region"] == region and d["from"] == frm), None)


p19 = contract_with(lambda d_: None, "c190.json")
c_, o_, s19 = build19(p19, "s190.json")
cal = era19(s19, "calabrio", 1815)
case("contract 1.9.0 (flags, no margin fields), DEFAULT policy: an approx era is kept with margin 0 on each side, recorded as the PROVISIONAL fallback "
     "(only the floor N = 5 then holds it: first usable year 1821, last 1855)",
     c_ == 0 and cal and (cal["approx"], cal["from_margin"], cal["to_margin"], cal["margin_src"], cal["margin_sourced"]) == (True, 0, 0, "fallback", None)
     and cal["margin_ok"] == {"kind": "approx", "first": 1821, "last": 1855} and s19["policy"]["approx"] == "margin" and s19["policy"]["contested"] == "scope"
     and s19["policy"]["margin_years"] == 5, o_)
cal2 = era19(s19, "calabrio", 1861)
case("...an approx era still running has only a start margin (no end bound), and its last allowed year is null (running on)",
     cal2 and (cal2["from_margin"], cal2["to_margin"], cal2["margin_ok"]) == (0, None, {"kind": "approx", "first": 1867, "last": None}), cal2)
case("...a contested era with NO contestedScope is refused by default (a contract before 1.10.0 does not say whether it is about the bounds), with its own counted reason",
     era19(s19, "scoped", 1816) is None and why19(s19, "scoped", 1816).startswith("contested (true) with no contestedScope"), s19.get("dropped"))
case("...the same for the regime-level and part-level eras (no scope)", era19(s19, "flat", 1900) is None and era19(s19, "flat", 1950) is None, s19.get("dropped"))
case("...a shorthand regime (feudal) is refused whatever its flags say; the contested era after it is refused for want of a scope",
     era19(s19, "feud", 1000) is None and why19(s19, "feud", 1000).startswith("regime is the project's own shorthand") and era19(s19, "feud", 1700) is None, s19.get("dropped"))
case("...an era the contract flags neither way carries no margin and no margin_ok (a contract with no margin fields gives it none)",
     era19(s19, "plain", 1700)["margin_ok"] is None and era19(s19, "plain", 1700)["from_margin"] is None)
snc = s19
case("what it built answers as the library does: 1830 keeps its note (rests on an approx era), 1820, 1856, 1859, 1861, 1862 and 1866 are silent, 1821, 1855 and 1867 are allowed",
     (eralib.era_at(snc, "Calabrio", 1830) or {}).get("approx") is True and [eralib.why_not(snc, "Calabrio", y) for y in (1820, 1856, 1859, 1861, 1862, 1866)] == ["margin"] * 6
     and eralib.why_not(snc, "Calabrio", 1821) == "ok" and eralib.why_not(snc, "Calabrio", 1855) == "ok" and eralib.why_not(snc, "Calabrio", 1867) == "ok", [eralib.why_not(snc, "Calabrio", y) for y in (1820, 1856, 1867)])
import checkera  # noqa: E402
case("...and the gate accepts the snapshot's shape", checkera.check_snapshot(s19) == [], checkera.check_snapshot(s19))
c_, o_, sr_ = build19(p19, "s190r.json", ["--approx", "refuse"])
case("--approx refuse drops an approx era again (counted)", c_ == 0 and era19(sr_, "calabrio", 1815) is None and why19(sr_, "calabrio", 1815) == "marked approximate (true)" and sr_["policy"]["approx"] == "refuse", o_)
c_, o_, sm_ = build19(p19, "s190m.json", ["--contested", "margin", "--margin-years", "8"])
sc_ = era19(sm_, "scoped", 1816)
case("--contested margin (the what-if for a contract with no scope) keeps a contested era with no scope, on the fallback; --margin-years moves the floor N (first usable 1824, last 1852)",
     sc_ and (sc_["contested_scope"], sc_["from_margin"], sc_["to_margin"], sc_["margin_src"]) == (None, 0, 0, "fallback") and sc_["margin_ok"] == {"kind": "contested", "first": 1825, "last": 1852}
     and era19(sm_, "calabrio", 1815)["margin_ok"] == {"kind": "approx", "first": 1824, "last": 1852}
     and sm_["policy"]["contested"] == "margin" and sm_["policy"]["margin_years"] == 8, (sc_, o_))
case("...but never a shorthand: 'feud' 1000 is refused, and its contested 1700 era is kept only because the what-if says so",
     era19(sm_, "feud", 1000) is None and era19(sm_, "feud", 1700) is not None and era19(sm_, "flat", 1900) is not None, sm_.get("dropped"))
c_, o_, sx_ = build19(p19, "s190x.json", ["--contested", "refuse"])
case("--contested refuse drops every contested era", all(era19(sx_, r_, f_) is None for r_, f_ in (("scoped", 1816), ("flat", 1900), ("feud", 1700))) and why19(sx_, "scoped", 1816) == "marked contested (true)", o_)
c_, o_, _ = build19(p19, "bad.json", ["--margin-years", "-1"])
case("--margin-years -1 is refused (exit 2)", c_ == 2, o_)
pb = contract_with(lambda d_: d_["regions"][1]["eras"][0].update(contestedScope="bounds"), "cb.json")
c_, o_, sb_ = build19(pb, "sb.json")
case("a bounds-contested era from a contract that gives no margins is refused: the fallback is for an approx era only", era19(sb_, "scoped", 1816) is None
     and why19(sb_, "scoped", 1816).startswith("flagged approximate or contested with no margin"), sb_.get("dropped"))


# the contract 1.10.0 shape: every era carries fromMargin / toMargin / contestedScope / marginSourced (null where nobody assessed it)
def to110(d_):
    d_["contract"]["version"] = "1.10.0"
    by = {r_["id"]: r_ for r_ in d_["regions"]}
    for r_ in d_["regions"]:
        for e_ in r_["eras"]:
            e_.update(fromMargin=0, toMargin=0 if e_["to"] is not None else None, contestedScope="none", marginSourced=True)
    cal_ = by["calabrio"]["eras"]
    cal_[0].update(fromMargin=1, toMargin=1)                                  # approx, with the Atlas's own margins (below the floor of 5)
    cal_[1].update(fromMargin=2)
    by["scoped"]["eras"][0].update(contestedScope="bounds", fromMargin=8, toMargin=3)
    by["scoped"]["eras"][1].update(fromMargin=1)
    by["flat"]["eras"][0].update(contestedScope="regime", fromMargin=1, toMargin=1)
    by["flat"]["eras"][1].update(contestedScope="part", fromMargin=1, toMargin=1)
    by["feud"]["eras"][0].update(contestedScope="bounds")
    by["feud"]["eras"][1].update(contestedScope="bounds")
    by["plain"]["eras"][0].update(fromMargin=3, toMargin=3, marginSourced=False)
    by["plain"]["eras"][1].update(fromMargin=None)                            # an unknowable start


p110 = contract_with(to110, "c1100.json")
c_, o_, s110 = build19(p110, "s1100.json")
cal = era19(s110, "calabrio", 1815)
case("synthetic contract 1.10.0: the Atlas's own fromMargin/toMargin are used (margin_src contract), the floor N = 5 lifts margins below it (first usable 1821, last 1855), "
     "and the version is recorded",
     c_ == 0 and (cal["from_margin"], cal["to_margin"], cal["margin_src"], cal["margin_sourced"]) == (1, 1, "contract", True)
     and cal["margin_ok"] == {"kind": "approx", "first": 1821, "last": 1855}
     and s110["contract"]["version"] == "1.10.0" and era19(s110, "calabrio", 1861)["margin_ok"] == {"kind": "approx", "first": 1867, "last": None}, cal)
sic = era19(s110, "scoped", 1816)
case("...a contested era whose contestedScope is 'bounds' is kept under the default (scope) policy; a margin ABOVE the floor is the reach (8 at the start, floor 5 at the end)",
     sic and (sic["contested"], sic["contested_scope"], sic["margin_src"], sic["margin_ok"]) == (True, "bounds", "contract", {"kind": "contested", "first": 1825, "last": 1855})
     and era19(s110, "scoped", 1861)["margin_ok"] == {"kind": "margin", "first": 1867, "last": None}, sic)
case("...a Fiume-like era (scope 'regime') and a 'part' era are refused whatever their margins, each with its own reason",
     era19(s110, "flat", 1900) is None and era19(s110, "flat", 1950) is None and why19(s110, "flat", 1900).startswith("contested about its regime or a part")
     and why19(s110, "flat", 1950).startswith("contested about its regime or a part"), s110.get("dropped"))
case("...a shorthand (feudal) era is refused even with a scope of bounds; the era after it is kept (first usable 1706, last 1794)",
     era19(s110, "feud", 1000) is None and era19(s110, "feud", 1700)["margin_ok"] == {"kind": "contested", "first": 1706, "last": 1794}, s110.get("dropped"))
pl = era19(s110, "plain", 1700)
case("...an unsourced margin (marginSourced false) is carried and makes the reach N more (3 -> 5 + 5: first usable 1711, last 1789), and is counted",
     pl and (pl["margin_sourced"], pl["margin_ok"]) == (False, {"kind": "margin", "first": 1711, "last": 1789}) and "eras_kept_with_unsourced_margin" in o_, pl)
case("...an era whose start margin is null (unknowable) is refused, with its own reason; the open end of an era still running needs no margin",
     era19(s110, "plain", 1800) is None and why19(s110, "plain", 1800).startswith("a bound whose margin is unknowable") and era19(s110, "calabrio", 1861) is not None, s110.get("dropped"))
case("...the answers on it: Calabrio 1830 noted, 1820 silent, 1821 noted; Scopetown 1824 silent, 1825 noted, 1855 noted, 1856 silent; Plainton 1710 silent, 1711 noted "
     "(rests on an unsourced margin), 1789 noted, 1790 silent; Feudton 1705 silent, 1706 noted; Fiumeish and Feudton 1500 silent",
     eralib.why_not(s110, "Calabrio", 1830) == "ok" and eralib.why_not(s110, "Calabrio", 1820) == "margin" and eralib.why_not(s110, "Calabrio", 1821) == "ok"
     and [eralib.why_not(s110, "Scopetown", y) for y in (1824, 1825, 1855, 1856)] == ["margin", "ok", "ok", "margin"]
     and [eralib.why_not(s110, "Plainton", y) for y in (1710, 1711, 1789, 1790)] == ["margin", "ok", "ok", "margin"]
     and (eralib.era_at(s110, "Plainton", 1711) or {}).get("unsourced") is True and (eralib.era_at(s110, "Scopetown", 1825) or {}).get("unsourced") is False
     and [eralib.why_not(s110, "Feudton", y) for y in (1705, 1706)] == ["margin", "ok"] and eralib.why_not(s110, "Flatville", 1925) == "era-refused"
     and eralib.why_not(s110, "Feudton", 1500) == "era-refused", [eralib.why_not(s110, "Scopetown", y) for y in (1824, 1825)])
# a shorthand regime is refused under EVERY policy
for pol_ in (["--contested", "refuse"], ["--contested", "scope"], ["--contested", "margin"], ["--approx", "refuse"], ["--approx", "margin", "--contested", "margin"]):
    c_, o_, sp_ = build19(p110, "s1100p.json", pol_)
    case("a shorthand (feudal) era is refused under %s" % " ".join(pol_), c_ == 0 and era19(sp_, "feud", 1000) is None and why19(sp_, "feud", 1000).startswith("regime is the project's own shorthand"), o_)
# the regime and part scopes are refused under every policy, margin included
c_, o_, sp_ = build19(p110, "s1100m.json", ["--contested", "margin"])
case("a contestedScope of regime or part is refused even under --contested margin", era19(sp_, "flat", 1900) is None and era19(sp_, "flat", 1950) is None and era19(sp_, "scoped", 1816) is not None, o_)
c_, o_, sp_ = build19(p110, "s1100r.json", ["--contested", "refuse"])
case("--contested refuse drops a bounds-scope era too", era19(sp_, "scoped", 1816) is None, o_)
# the archive may widen an era's margin, never narrow it
mp_ = os.path.join(tmp, "margins.json")
json.dump({"calabrio--era-1815": 9, "scoped--era-1816": {"from": 2, "to": 6}, "_note": "x"}, open(mp_, "w"))
c_, o_, sw_ = build19(p110, "s1100w.json", ["--margins", mp_])
cal, sic = era19(sw_, "calabrio", 1815), era19(sw_, "scoped", 1816)
case("--margins widens a margin the contract gave (1 -> 9, src archive), and cannot narrow it (contract 8 keeps 8 where the file says 2; 3 -> 6); the policy records the file",
     (cal["from_margin"], cal["to_margin"], cal["margin_src"]) == (9, 9, "archive") and (sic["from_margin"], sic["to_margin"], sic["margin_src"]) == (8, 6, "archive")
     and sw_["policy"]["margins"] == {"calabrio--era-1815": {"from": 9, "to": 9}, "scoped--era-1816": {"from": 2, "to": 6}}, (cal, sic))
c_, o_, sw_ = build19(p19, "s190w.json", ["--margins", mp_])
cal = era19(sw_, "calabrio", 1815)
case("...on a contract with no margins the archive's figure replaces the fallback for that era (src archive) and the other eras keep the fallback",
     (cal["from_margin"], cal["to_margin"], cal["margin_src"]) == (9, 9, "archive") and era19(sw_, "calabrio", 1861)["margin_src"] == "fallback", cal)
pn = contract_with(lambda d_: (to110(d_), d_["regions"][0]["eras"][0].update(fromMargin=-3, toMargin="two")), "cn2.json")
c_, o_, sn2_ = build19(pn, "sn2.json")
case("a margin that is not a whole number of years >= 0 is no margin: the era is refused as unknowable (never replaced by the fallback)", era19(sn2_, "calabrio", 1815) is None
     and why19(sn2_, "calabrio", 1815).startswith("a bound whose margin is unknowable"), sn2_.get("dropped"))
pnn = contract_with(lambda d_: (to110(d_), d_["regions"][0]["eras"][0].update(toMargin=None)), "cn3.json")
c_, o_, sn3_ = build19(pnn, "sn3.json")
case("a null toMargin on a CLOSED era is unknowable: refused", era19(sn3_, "calabrio", 1815) is None, sn3_.get("dropped"))
pnu = contract_with(lambda d_: (to110(d_), d_["regions"][0]["eras"][0].update(approx=None, contested=None, fromMargin=None, toMargin=None)), "cn4.json")
c_, o_, sn4_ = build19(pnu, "sn4.json", ["--unassessed", "allow"])
case("an unassessed era (flags null, margins null) is refused as unknowable even under --unassessed allow", era19(sn4_, "calabrio", 1815) is None
     and why19(sn4_, "calabrio", 1815).startswith("a bound whose margin is unknowable"), sn4_.get("dropped"))
case("the snapshots built from 1.10.0 pass the gate's shape check", checkera.check_snapshot(s110) == [] and checkera.check_snapshot(sw_) == [] and checkera.check_snapshot(sp_) == [], checkera.check_snapshot(s110))
c_, o_, _ = build19(p110, "s1100.json", ["--check"])
case("--check passes on the rebuilt margin snapshot", c_ == 0, o_)

# ---------------------------------------------------------------- 2c. erasnap.py: rule m, the rulers
print("erasnap.py: the contract's rulers are carried, or refused whole, and never read from a missing field")


def rrow(name, polity, fy, ty, fm=0, tm=0, frm=None, to="auto", q=None, **kw):
    r_ = {"name": name, "polity": "Kingdom of X (free text)", "from": frm or str(fy), "to": (str(ty) if ty is not None else None) if to == "auto" else to,
          "fromYear": fy, "toYear": ty, "polityId": polity, "fromMargin": fm, "toMargin": tm, "marginWhy": "invented", "source": "https://atlas.example.test/r", "note": "a long note"}
    if q:
        r_["q"] = q
    r_.update(kw)
    return r_


def rregion(rid, lat, **kw):
    r_ = mk_region(rid, lat, [ce(rid, 1700, None, regime="kingdom", label="Kingdom of X")])
    r_.update(kw)
    return r_


GOOD = [rrow("Alpha I", "kingdom-of-x", 1700, 1750, frm="1700-01-02", to="1750-03-04", q="Q5"), rrow("Alpha II", "kingdom-of-x", 1750, None, to=None, frm="1750-03-04")]
C12 = copy.deepcopy(C19)
C12["contract"]["version"] = "1.12.0"
C12["regions"] = [
    rregion("hasr", 0, hasRulers=True, hasLanguage=False, rulers=GOOD),
    rregion("norulers", 10, hasRulers=False, hasLanguage=False),
    rregion("nofield", 20),
    rregion("nullmargin", 30, hasRulers=True, rulers=[rrow("A", "kingdom-of-x", 1700, 1750, tm=None)]),
    rregion("badyears", 40, hasRulers=True, rulers=[rrow("A", "kingdom-of-x", 1701, 1750, frm="1700-01-01")]),
    rregion("noend", 50, hasRulers=True, rulers=[{k: v for k, v in rrow("A", "kingdom-of-x", 1700, 1750).items() if k != "toYear"}]),
    rregion("openbad", 60, hasRulers=True, rulers=[rrow("A", "kingdom-of-x", 1700, 1750, to=None)]),
    rregion("emptyrows", 70, hasRulers=True, rulers=[]),
    rregion("strangeyear", 80, hasRulers=True, rulers=[rrow("A", "kingdom-of-x", 1700, "1750")]),
    rregion("badslug", 90, hasRulers=True, rulers=[rrow("A", "Kingdom Of X", 1700, 1750)]),
    rregion("noname", 100, hasRulers=True, rulers=[rrow("  ", "kingdom-of-x", 1700, 1750)]),
    rregion("hasrtext", 110, hasRulers="yes", rulers=GOOD),
    rregion("unusedr", 120, hasRulers=True, rulers=GOOD),
]
T12 = {"places": {"Has Town": "hasr", "Plain Town": "norulers", "Nofield Town": "nofield", "Nullm Town": "nullmargin", "Years Town": "badyears", "Noend Town": "noend",
                  "Open Town": "openbad", "Empty Town": "emptyrows", "Strange Town": "strangeyear", "Slug Town": "badslug", "Noname Town": "noname", "Text Town": "hasrtext"}}
p12 = os.path.join(tmp, "c120.json")
json.dump(C12, open(p12, "w"))
KP = os.path.join(tmp, "kp.json")
json.dump({"kingdom": ["kingdom-of-x"]}, open(KP, "w"))
c_, o_, s12 = build19(p12, "s120.json", table=T12)
R12 = s12.get("rulers", {})
case("it carries the rulers of every region the snapshot holds, and only those (a region no place uses is not carried)",
     c_ == 0 and sorted(R12) == sorted(r_["id"] for r_ in C12["regions"] if r_["id"] != "unusedr") and "regions_with_rulers" in o_, (o_, sorted(R12)))
case("a region the contract marks hasRulers true, with usable rows, has them: the Atlas's own name, polityId, the dates as stated, the numeric years and margins, q and source; not the note or the polity string",
     R12["hasr"]["has"] is True and R12["hasr"]["why"] is None and R12["hasr"]["reigns"][0] == {
         "name": "Alpha I", "polity_id": "kingdom-of-x", "from": "1700-01-02", "to": "1750-03-04", "from_year": 1700, "to_year": 1750, "from_margin": 0, "to_margin": 0,
         "margin_why": "invented", "q": "Q5", "source": "https://atlas.example.test/r"} and R12["hasr"]["reigns"][1]["to_year"] is None and R12["hasr"]["reigns"][1]["q"] is None
     and "note" not in R12["hasr"]["reigns"][0] and "polity" not in R12["hasr"]["reigns"][0], R12.get("hasr"))
case("hasRulers false is recorded as false, with why and no reigns; a region the contract does not state is null (a missing field is never read as none)",
     R12["norulers"] == {"has": False, "why": "the contract says the region has no rulers", "reigns": []}
     and R12["nofield"] == {"has": None, "why": "the contract has no hasRulers for this region", "reigns": []}, (R12["norulers"], R12["nofield"]))
case("hasRulers that is not true (a string) is not true", R12["hasrtext"]["has"] is False and R12["hasrtext"]["reigns"] == [])
refused = {k: R12[k] for k in ("nullmargin", "badyears", "noend", "openbad", "emptyrows", "strangeyear", "badslug", "noname")}
case("ONE unusable row refuses the whole region's rulers (a null margin is unknowable; years that do not follow the dates stated; a closed reign with no toYear, which would read as one that goes on for ever; an open reign with a toYear; "
     "no rows; a string year; a polityId that is not a slug; a name with nothing in it), and says why",
     all(v["has"] is False and v["reigns"] == [] and v["why"] for v in refused.values()), refused)
case("the output counts regions with rulers, reigns carried and regions refused for an unusable row", any(l.split()[:2] == ["regions_with_rulers", "1"] for l in o_.splitlines())
     and any(l.split()[:2] == ["reigns_carried", "2"] for l in o_.splitlines()) and any(l.split()[:2] == ["regions_with_rulers_refused", "8"] for l in o_.splitlines()), o_)
case("the policy records the polities each regime may name a ruler of (the kit's default: twosicilies and italy)", s12["policy"]["ruler_polities"] == {
    "italy": ["kingdom-of-italy", "italian-republic"], "twosicilies": ["kingdom-of-the-two-sicilies"]}, s12.get("policy"))
case("...so an era of another regime names no ruler, though the region has them",
     eralib.era_at(s12, "Has Town", 1725)["ruler"] is None and eralib.why_no_ruler(s12, "hasr", 1725) == "polity")
c_, o_, s12k = build19(p12, "s120k.json", ["--ruler-polities", KP], table=T12)
case("--ruler-polities replaces the table, and is recorded: the same snapshot now names Alpha I in 1725, Alpha II in 1760 (an open reign)",
     c_ == 0 and s12k["policy"]["ruler_polities"] == {"kingdom": ["kingdom-of-x"]} and (eralib.era_at(s12k, "Has Town", 1725)["ruler"] or {}).get("name") == "Alpha I"
     and (eralib.era_at(s12k, "Has Town", 1760)["ruler"] or {}).get("name") == "Alpha II", o_)
case("...and no ruler where the year is within the margin of a reign, in a region with none, a region unstated, or one whose rows were unusable",
     eralib.era_at(s12k, "Has Town", 1748)["ruler"] is None and all(eralib.era_at(s12k, pl, 1725) is not None and eralib.era_at(s12k, pl, 1725)["ruler"] is None
                                                                      for pl in ("Plain Town", "Nofield Town", "Nullm Town", "Years Town", "Noend Town", "Open Town", "Empty Town", "Strange Town", "Slug Town", "Noname Town", "Text Town")))
case("the snapshots built with rulers pass the gate's shape check", checkera.check_snapshot(s12) == [] and checkera.check_snapshot(s12k) == [], (checkera.check_snapshot(s12), checkera.check_snapshot(s12k)))
c_, o_, _ = build19(p12, "s120k.json", ["--ruler-polities", KP, "--check"], table=T12)
case("--check passes on the rebuilt snapshot, with the rulers and the table", c_ == 0, o_)
json.dump(["not", "an", "object"], open(KP, "w"))
c_, o_, _ = build19(p12, "s120x.json", ["--ruler-polities", KP], table=T12)
case("a --ruler-polities file that is not {regime: [slug, ...]} is refused", c_ != 0 and "ruler-polities" in o_, o_)
p_old = contract_with(lambda d_: d_["contract"].update(version="1.10.0"), "c1100r.json")
c_, o_, s_old = build19(p_old, "s_old.json", table={"places": {"Calabrio": "calabrio"}})
case("a contract before the rulers (no hasRulers at all) gives has null for its regions: no ruler, and the snapshot is still well formed",
     c_ == 0 and all(v["has"] is None for v in s_old["rulers"].values()) and checkera.check_snapshot(s_old) == [], o_)
for tag, mut, expect in (
        ("a region marked as having rulers whose reigns are unusable", lambda sn: sn["rulers"]["hasr"]["reigns"][0].update(to_year="c. 1750"), True),
        ("a region marked as having rulers with no reigns", lambda sn: sn["rulers"]["hasr"].update(reigns=[]), True),
        ("a region without rulers that carries reigns", lambda sn: sn["rulers"]["norulers"].update(reigns=copy.deepcopy(sn["rulers"]["hasr"]["reigns"])), True),
        ("a region without rulers that does not say why", lambda sn: sn["rulers"]["norulers"].update(why=None), True),
        ("rulers for a region the snapshot does not hold", lambda sn: sn["rulers"].update(narnia={"has": False, "why": "x", "reigns": []}), True),
        ("a has that is not true, false or null", lambda sn: sn["rulers"]["hasr"].update(has="yes"), True),
        ("no rulers at all", lambda sn: sn.pop("rulers"), True),
        ("a policy without ruler_polities", lambda sn: sn["policy"].pop("ruler_polities"), True),
        ("a ruler_polities entry that is not a list of slugs", lambda sn: sn["policy"].update(ruler_polities={"kingdom": "kingdom-of-x"}), True)):
    sn_ = copy.deepcopy(s12k)
    mut(sn_)
    case("the gate's shape check: %s is malformed" % tag, bool(checkera.check_snapshot(sn_)) == expect, checkera.check_snapshot(sn_))

# ---------------------------------------------------------------- 3. checkera.py
print("checkera.py: a planted fault for each rule")
CLEAN = CASES["gate_snapshot"]
ERA_URL = "https://atlas.example.test/region/%s/#era-%s"


PLACE_OF = {"ruritania": "hentzau", "elphberg": "zenda"}


def note(id_="ruritania--era-1700", year="1750", label="Kingdom of Ruritania", src="per the Record Atlas", href=ERA_URL % ("ruritania", 1700), boundary=False,
         pre=None, assessed="1", edge=False, approx=False, contested=False, unsourced=False, place=True, ruler=None, extra=""):
    a = '<a class="era-src" href="%s" rel="noopener">%s</a>' % (href, src) if href else '<span class="era-src">%s</span>' % src
    b = ' data-era-boundary="1"' if boundary else ""
    m = (' data-era-assessed="%s"' % assessed if assessed is not None else "") + (' data-era-approx="1"' if approx else "") + (' data-era-contested="1"' if contested else "") + (' data-era-margin-unsourced="1"' if unsourced else "") + (' data-era-edge-agree="1"' if edge else "")
    place = PLACE_OF.get(id_.split("--")[0]) if place is True else place
    m += (' data-era-place="%s"' % place if place else "") + (' data-era-ruler="%s"' % ruler if ruler else "")
    pre = pre if pre is not None else ("· From that year: " if boundary else "· At the time: ")
    ru = ' <span class="era-ruler">(%s)</span>' % ruler if ruler else ""
    return ('<span class="era-note" data-era="%s" data-era-year="%s"%s%s><span class="era-pre">%s</span>'
            '<span class="era-lab">%s</span>%s %s%s</span>' % (id_, year, b, m, pre, label, ru, a, extra))


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
APX = lambda y, **k: page(note("ruritania--era-1800", str(y), "Occupied Ruritania", href=ERA_URL % ("ruritania", 1800), approx=True, **k))
c, o = gate({P: APX(1825)})
case("control: a note on an approximate era, well inside it and marked approx, passes and is counted as resting on an approximate era, on the PROVISIONAL floor",
     c == 0 and "1 on an approximate era and 0 on a contested one" in o and "1 of them on the PROVISIONAL floor alone" in o and "0 resting on an UNSOURCED margin" in o, o)
fails("a note on an approximate era that does not say so (no data-era-approx) fails (approx)", {P: page(note("ruritania--era-1800", "1825", "Occupied Ruritania", href=ERA_URL % ("ruritania", 1800)))}, "approx 1")
fails("a note marked approx on an era the snapshot does not flag fails (approx)", {P: page(note(approx=True))}, "approx 1")
fails("a note on an approximate era within the margin of its start (5 years: not MORE than 5) fails (margin)", {P: APX(1805)}, "margin 1")
fails("...and 1806 passes", {P: APX(1806)}, "1 note(s)", code=0)
fails("a note on an approximate era within the margin of its end (1845: 5 years) fails (margin)", {P: APX(1845)}, "margin 1")
fails("...and 1844 passes", {P: APX(1844)}, "1 note(s)", code=0)
fails("a note on an approximate era in the boundary year (a boundary year is within any margin) fails (margin)", {P: page(note("ruritania--era-1800", "1800", "Occupied Ruritania", href=ERA_URL % ("ruritania", 1800), approx=True, boundary=True))}, "margin 1")
s = copy.deepcopy(CLEAN); s["policy"]["approx"] = "refuse"
fails("an approximate era in a snapshot whose policy refuses approximate eras (malformed snapshot)", {P: APX(1825)}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][1]["margin_ok"] = {"kind": "approx", "first": 1800, "last": 1849}
fails("an era whose recorded margin_ok does not follow its margins (malformed snapshot)", {P: APX(1825)}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][1]["to_margin"] = None; s["regions"]["ruritania"][1]["margin_ok"] = None
fails("a flagged era with a margin missing (malformed snapshot)", {P: APX(1825)}, "malformed", s)
s = copy.deepcopy(CLEAN); s["regions"]["ruritania"][0]["contested"] = True
fails("a contested era the policy would refuse (scope with no scope; malformed snapshot)", {P: page(note())}, "malformed", s)
s = copy.deepcopy(CLEAN); e_ = s["regions"]["ruritania"][0]; e_.update(contested=True, contested_scope="regime", from_margin=1, to_margin=1); e_["margin_ok"] = eralib.margin_span(e_, 5)
fails("a contested era of scope regime kept in the snapshot (malformed snapshot)", {P: page(note(year="1760", contested=True))}, "malformed", s)
s = copy.deepcopy(CLEAN); e_ = s["regions"]["ruritania"][0]; e_.update(contested=True, contested_scope="bounds", from_margin=1, to_margin=1, margin_src="contract"); e_["margin_ok"] = eralib.margin_span(e_, 5)
c, o = gate({P: page(note(year="1760", contested=True))}, s)
case("control: a note on an era contested about its bounds, well inside it and marked contested, passes and is counted", c == 0 and "0 on an approximate era and 1 on a contested one" in o, o)
fails("...a note on it within its margin of the start (1701) fails (margin)", {P: page(note(year="1701", contested=True))}, "margin 1", s)
fails("...a note on it that does not say it is contested fails (approx)", {P: page(note(year="1760"))}, "approx 1", s)
s = copy.deepcopy(CLEAN); e_ = s["regions"]["ruritania"][0]; e_.update(from_margin=3, to_margin=3, margin_src="contract", margin_sourced=False); e_["margin_ok"] = eralib.margin_span(e_, 5)
c, o = gate({P: page(note(year="1760", unsourced=True))}, s)
case("control: a note on a clean era whose margin the Atlas did not source (reach 3 -> 5 + 5), well inside it and marked, passes and is counted as resting on an unsourced margin",
     c == 0 and "1 resting on an UNSOURCED margin" in o, o)
fails("...a note on it that does not say so (no data-era-margin-unsourced) fails (approx)", {P: page(note(year="1760"))}, "approx 1", s)
fails("...a note on it at 1710 (10 years from the start: not MORE than 5 + 5) fails (margin)", {P: page(note(year="1710", unsourced=True))}, "margin 1", s)
fails("...and 1711 passes", {P: page(note(year="1711", unsourced=True))}, "1 note(s)", s, code=0)
fails("a note marked unsourced on an era whose margin the Atlas sourced fails (approx)", {P: page(note(year="1760", unsourced=True))}, "approx 1")
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
s["regions"]["elphberg"].insert(0, dict(s["regions"]["elphberg"][0], id="elphberg--era-1700", **{"from": 1700, "to": 1900, "present": False, "url": "/region/elphberg/#era-1700",
                                                                                                    "seeded_from_archive": False, "basis": "not-recorded"}))
c, o = gate({P: page(note(edge=True, place="edgy"))}, s)
case("control: an edge-agree mark where the snapshot holds such a place passes, and is counted", c == 0 and "1 at an edge where every neighbour agrees" in o and "(0 not edge-checked, 1 at an edge)" in o, o)
print("  the re-derivation: every mark of a built note is recomputed from the snapshot, its place and its year (missing, extra or wrong all fail)")
RS = CASES["other_snapshots"]["rulers"]


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def draw(place, year, rulers=False, snap=None):
    """A note as lib/era.js renderEra draws it (the Python twin of the markup, held to the JS one by the component test in era_logic.mjs)."""
    e = eralib.era_at(snap or RS, place, year)
    ru = e["ruler"] if rulers and e["ruler"] else None
    a = '<a class="era-src" href="%s" rel="noopener">%s</a>' % (esc(e["href"]), esc(e["source"])) if e["href"] else '<span class="era-src">%s</span>' % esc(e["source"])
    return ('<span class="era-note" data-era="%s" data-era-year="%s"%s data-era-assessed="%s"%s%s%s%s data-era-place="%s"%s><span class="era-pre">%s</span><span class="era-lab">%s</span>%s %s</span>'
            % (esc(e["id"]), e["year"], ' data-era-boundary="1"' if e["boundary"] else "", "1" if e["assessed"] else "0", ' data-era-approx="1"' if e["approx"] else "",
               ' data-era-contested="1"' if e["contested"] else "", ' data-era-margin-unsourced="1"' if e["unsourced"] else "", ' data-era-edge-agree="1"' if e["edgeAgree"] else "",
               esc(e["place"]), ' data-era-ruler="%s"' % esc(ru["name"]) if ru else "", eralib.PRE_BOUNDARY if e["boundary"] else eralib.PRE_NORMAL, esc(e["label"]),
               ' <span class="era-ruler">(%s)</span>' % esc(ru["name"]) if ru else "", a))


def rfails(label, body, cat, extra=None, code=1):
    c, o = gate({P: page(body)}, RS, extra)
    case(label, c == code and (cat is None or cat in o), "exit %s: %s" % (c, o))


MARKS = [("data-era-boundary", "Tidy Town", 1800, ' data-era-boundary="1"', "boundary 1"), ("data-era-assessed", "Rulertown", 1745, ' data-era-assessed="1"', "assessed 1"),
         ("data-era-approx", "Rulertown", 1830, ' data-era-approx="1"', "approx 1"), ("data-era-contested", "Dispute Town", 1750, ' data-era-contested="1"', "approx 1"),
         ("data-era-margin-unsourced", "Soft Town", 1750, ' data-era-margin-unsourced="1"', "approx 1"), ("data-era-edge-agree", "Rulerborder Town", 1750, ' data-era-edge-agree="1"', "edge 1"),
         ("data-era-place", "Rulertown", 1745, ' data-era-place="rulertown"', "place 1")]
for mark, place, year, attr, cat in MARKS:
    base_ = draw(place, year)
    c, o = gate({P: page(base_)}, RS)
    case("control: the %s note the library draws for %s %s carries %s and passes" % (place, year, mark, mark), c == 0 and attr in base_, o)
    rfails("the same note with %s REMOVED fails (%s)" % (mark, cat.split()[0]), base_.replace(attr, ""), cat)
for mark, place, year, attr, cat in MARKS:
    if mark in ("data-era-assessed", "data-era-place"):
        continue
    plain_ = draw("Rulertown", 1745)
    rfails("a note with %s ADDED where the snapshot does not give it fails (%s)" % (mark, cat.split()[0]), plain_.replace(' data-era-place="rulertown"', attr + ' data-era-place="rulertown"'), cat)
rfails("data-era-assessed with the wrong value fails (assessed)", draw("Rulertown", 1745).replace('data-era-assessed="1"', 'data-era-assessed="0"'), "assessed 1")
rfails("a note drawn for another place of another region (same year) fails (place)", draw("Rulertown", 1745).replace('data-era-place="rulertown"', 'data-era-place="plain town"'), "place 1")
rfails("a note drawn for a place the snapshot does not map fails (place)", draw("Rulertown", 1745).replace('data-era-place="rulertown"', 'data-era-place="nowhere"'), "place 1")
rfails("a place that is not the folded key fails (place)", draw("Rulertown", 1745).replace('data-era-place="rulertown"', 'data-era-place="Rulertown"'), "place 1")
rfails("a note for a place and year the library would not draw at all fails (silent)", draw("Rulertown", 1745).replace('data-era-year="1745"', 'data-era-year="1860"'), "silent 1")
rfails("text added inside the note fails (text)", draw("Rulertown", 1745).replace("</a></span>", "</a> (and more)</span>"), "text 1")
rfails("the label changed fails (label and text)", draw("Rulertown", 1745).replace("Kingdom of Ruritania", "Kingdom of Ruritania, Greater"), "label 1")
print("  rule m: rulers")
bare_, withr_ = draw("Rulertown", 1745), draw("Rulertown", 1745, True)
c, o = gate({P: page(withr_)}, RS, ["--rulers"])
case("control: a note that names the Atlas's ruler passes, is counted, and the summary says rulers are opted in", c == 0 and "1 note(s) name a ruler" in o and "rulers are opted in" in o, o)
c, o = gate({P: page(withr_)}, RS)
case("...and passes without --rulers (a ruler that is there is verified either way)", c == 0 and "rulers are not opted in" in o, o)
c, o = gate({P: page(bare_)}, RS)
case("a note with no ruler passes without --rulers: the archive has not opted in", c == 0, o)
rfails("...and fails with --rulers, where the snapshot names a ruler the note leaves out (ruler)", bare_, "ruler 1", ["--rulers"])
c, o = gate({P: page(draw("Rulertown", 1736, True))}, RS, ["--rulers"])
case("a year within a reign's margin carries no ruler and passes with --rulers", c == 0 and "0 note(s) name a ruler" in o, o)


def inject(html, name):
    return html.replace(' data-era-place="', ' data-era-place="', 1).replace('"><span class="era-pre">', '" data-era-ruler="%s"><span class="era-pre">' % name, 1).replace(
        '</span> <a class="era-src"', '</span> <span class="era-ruler">(%s)</span> <a class="era-src"' % name, 1)


for label, html in (("a ruler other than the one the snapshot names for the year", inject(bare_, "Rudolf I")),
                    ("the Atlas's name normalised (\"Rudolf 2\")", inject(bare_, "Rudolf 2")),
                    ("a ruler on a year within a reign's margin of its end (1736)", inject(draw("Rulertown", 1736), "Rudolf I")),
                    ("a ruler on an overlap year (1830: two reigns)", inject(draw("Rulertown", 1830), "Francis")),
                    ("a ruler of another polity than the era's regime allows (1770)", inject(draw("Rulertown", 1770), "Karl the Elder")),
                    ("a ruler on a boundary-year note", inject(draw("Tidy Town", 1800), "Tidy Karl")),
                    ("a ruler on an edge note", inject(draw("Rulerborder Town", 1750), "Rudolf II")),
                    ("a ruler on a note of a region the contract says has no rulers", inject(draw("Plain Town", 1750), "Plain King")),
                    ("a ruler on a note of a region with no rulers entry at all", inject(draw("Nofield Town", 1750), "Nobody")),
                    ("a ruler's words without the data-era-ruler mark", withr_.replace(' data-era-ruler="Rudolf II"', "")),
                    ("a data-era-ruler mark without its words", withr_.replace(' <span class="era-ruler">(Rudolf II)</span>', "")),
                    ("a ruler mark whose words differ", withr_.replace("(Rudolf II)", "(Rudolf the Second)")),
                    ("an empty ruler mark", withr_.replace('data-era-ruler="Rudolf II"', 'data-era-ruler=""'))):
    rfails(label + " fails (ruler)", html, "ruler 1", ["--rulers"])
c, o = gate({P: page(draw("Rulertown", 1888, True))}, RS, ["--rulers"])
case("the Atlas's name with an ampersand, an accent and brackets, escaped, passes exactly", c == 0, o)
s = copy.deepcopy(RS); s["rulers"]["rulerland"]["reigns"][1]["name"] = "Rudolf II "
c, o = gate({P: page(draw("Rulertown", 1745, True, s))}, s, ["--rulers"])
case("a name with a trailing space is the Atlas's name: the gate holds the attribute to it exactly", c == 0, o)

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
